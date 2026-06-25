"""The async moodboard generation pipeline.

``resolve_plan`` turns a generate request (saved brief or inline brief) into the
``input`` the worker reads. ``run_generation`` is the background task: for each
direction it authors a concept (LLM), renders tiles (image provider), stores the
assets, and assembles a self-contained HTML file — updating the DB row at each phase
so the SSE stream reflects progress.
"""

import asyncio
import mimetypes

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import session_scope
from app.models.brief import BriefSession
from app.models.moodboard import GenerationRequest, Moodboard
from app.providers import get_images, get_llm, get_storage
from app.schemas.brief import BriefContent
from app.schemas.moodboard import GenerateRequest
from app.services import directions as directions_svc
from app.services.htmlgen import assemble_html


async def resolve_plan(db: AsyncSession, owner: str, req: GenerateRequest) -> dict:
    """Build the worker ``input`` ({brief_text, directions:[{name,notes}]}).

    Raises ``LookupError`` (brief not found / not owned) or ``ValueError`` (no
    matching directions) — the router maps these to 404 / 400.
    """
    if req.brief_id:
        session = await db.get(BriefSession, req.brief_id)
        if session is None or session.owner != owner:
            raise LookupError("brief not found")
        content = BriefContent(**session.state)
        brief_text = directions_svc.brief_to_text(content)
        dirs = content.directions or directions_svc.compose_directions(content)[0]
        if req.directions:
            wanted = set(req.directions)
            dirs = [d for d in dirs if d.name in wanted]
            if not dirs:
                raise ValueError("none of the requested directions exist on this brief")
        plan_dirs = [
            {"name": d.name, "notes": directions_svc.direction_notes(content, d)} for d in dirs
        ]
        return {"brief_text": brief_text, "directions": plan_dirs}

    # Inline standalone brief.
    brief = req.brief
    assert brief is not None  # guaranteed by GenerateRequest validator
    parts = [brief.prompt]
    if brief.palette_hint:
        parts.append("Palette hints: " + ", ".join(brief.palette_hint))
    if brief.references:
        parts.append("References: " + "; ".join(brief.references))
    names = req.directions or brief.directions or ["Your brief"]
    return {
        "brief_text": "\n".join(parts),
        "directions": [{"name": n, "notes": []} for n in names],
    }


async def run_generation(request_id: str) -> None:
    """Background task: render every moodboard in the request."""
    llm = get_llm()
    images = get_images()
    storage = get_storage()

    async with session_scope() as db:
        req = await db.get(GenerationRequest, request_id)
        if req is None:
            return
        req.status = "running"
        plan = req.input or {}
        await db.commit()
        rows = (
            await db.execute(select(Moodboard).where(Moodboard.request_id == request_id))
        ).scalars().all()
        targets = [(m.id, m.direction_name) for m in rows]

    brief_text = plan.get("brief_text", "")
    notes_by_dir = {d["name"]: d.get("notes", []) for d in plan.get("directions", [])}

    results: list[bool] = []
    for mb_id, direction in targets:
        results.append(
            await _generate_one(
                mb_id, direction, brief_text, notes_by_dir.get(direction, []), llm, images, storage
            )
        )

    async with session_scope() as db:
        req = await db.get(GenerationRequest, request_id)
        if req is not None:
            if all(results):
                req.status = "done"
            elif any(results):
                req.status = "partial"
            else:
                req.status = "error"
                req.error = "all directions failed to generate"
            await db.commit()


async def _set_status(mb_id: str, **fields) -> None:
    async with session_scope() as db:
        mb = await db.get(Moodboard, mb_id)
        if mb is None:
            return
        for key, value in fields.items():
            setattr(mb, key, value)
        await db.commit()


async def _generate_one(mb_id, direction, brief_text, notes, llm, images, storage) -> bool:
    try:
        await _set_status(mb_id, status="composing")
        comp = await llm.author_moodboard(brief_text, direction, notes)
        palette = [s.model_dump() for s in comp.palette]
        await _set_status(
            mb_id,
            status="rendering",
            concept={"title": comp.title, "summary": comp.summary, "notes": comp.notes},
            palette=palette,
        )

        rendered: list[dict] = []  # for the HTML (carries bytes)
        image_refs: list[dict] = []  # for the DB / API response
        for idx, spec in enumerate(comp.images):
            data, content_type = await images.render(spec.prompt, idx)
            ext = mimetypes.guess_extension(content_type) or ".png"
            key = f"{mb_id}/{idx}{ext}"
            await asyncio.to_thread(storage.put, key, data, content_type)
            rendered.append({"data": data, "content_type": content_type, "alt": spec.alt})
            image_refs.append({"index": idx, "key": key, "prompt": spec.prompt, "alt": spec.alt})

        await _set_status(mb_id, status="assembling", images=image_refs)

        html = assemble_html(
            title=comp.title,
            summary=comp.summary,
            notes=comp.notes,
            palette=palette,
            images=rendered,
        )
        await _set_status(mb_id, status="done", html=html)
        return True
    except Exception as exc:  # noqa: BLE001 — record failure, don't crash the worker
        await _set_status(mb_id, status="error", error=f"{type(exc).__name__}: {exc}")
        return False
