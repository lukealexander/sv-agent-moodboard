"""Moodboard generation endpoints.

Usable on its own (generate from an inline brief, no briefing required) or fed a saved
``brief_id``. Generation is async via ``BackgroundTasks``; progress streams over SSE.
The shareable HTML is served here behind auth (a cross-service "store & share"
workflow will supersede this later — see TODO).
"""

import asyncio

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.auth import require_auth
from app.ids import new_id
from app.models.moodboard import GenerationRequest, Moodboard
from app.providers import get_storage
from app.schemas.moodboard import (
    GenerateRequest,
    GenerationRequestResponse,
    ImageRef,
    MoodboardResponse,
    MoodboardSummary,
)
from app.services import generation
from app.services.events import request_event_stream

router = APIRouter(prefix="/moodboards", tags=["moodboards"], dependencies=[Depends(require_auth)])


def _owner(claims: dict) -> str:
    return claims.get("sub") or "unknown"


async def _load_request(db: AsyncSession, request_id: str, owner: str) -> GenerationRequest:
    req = await db.get(GenerationRequest, request_id)
    if req is None or req.owner != owner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="request not found")
    return req


async def _load_moodboard(db: AsyncSession, moodboard_id: str, owner: str) -> Moodboard:
    mb = await db.get(Moodboard, moodboard_id)
    if mb is None or mb.owner != owner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="moodboard not found")
    return mb


async def _request_response(db: AsyncSession, req: GenerationRequest) -> GenerationRequestResponse:
    rows = (
        await db.execute(select(Moodboard).where(Moodboard.request_id == req.id))
    ).scalars().all()
    return GenerationRequestResponse(
        id=req.id,
        status=req.status,
        brief_id=req.brief_id,
        error=req.error,
        moodboards=[
            MoodboardSummary(id=m.id, direction_name=m.direction_name, status=m.status)
            for m in rows
        ],
    )


def _moodboard_response(mb: Moodboard) -> MoodboardResponse:
    storage = get_storage()
    images: list[ImageRef] = []
    for ref in mb.images or []:
        url = storage.url(ref["key"]) or f"/moodboards/{mb.id}/image/{ref['index']}"
        images.append(
            ImageRef(index=ref["index"], url=url, prompt=ref["prompt"], alt=ref["alt"])
        )
    return MoodboardResponse(
        id=mb.id,
        request_id=mb.request_id,
        direction_name=mb.direction_name,
        status=mb.status,
        concept=mb.concept,
        palette=mb.palette,
        images=images,
        html_url=f"/moodboards/{mb.id}/html" if mb.html else None,
        error=mb.error,
    )


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def create_generation(
    req: GenerateRequest,
    background: BackgroundTasks,
    user: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> GenerationRequestResponse:
    owner = _owner(user)
    try:
        plan = await generation.resolve_plan(db, owner, req)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    request_id = new_id()
    db.add(
        GenerationRequest(
            id=request_id, owner=owner, brief_id=req.brief_id, input=plan, status="queued"
        )
    )
    summaries: list[MoodboardSummary] = []
    for direction in plan["directions"]:
        mb = Moodboard(
            id=new_id(),
            request_id=request_id,
            owner=owner,
            direction_name=direction["name"],
            status="queued",
        )
        db.add(mb)
        summaries.append(
            MoodboardSummary(id=mb.id, direction_name=mb.direction_name, status="queued")
        )
    await db.commit()

    background.add_task(generation.run_generation, request_id)
    return GenerationRequestResponse(
        id=request_id, status="queued", brief_id=req.brief_id, moodboards=summaries
    )


@router.get("/requests/{request_id}")
async def get_request(
    request_id: str, user: dict = Depends(require_auth), db: AsyncSession = Depends(get_db)
) -> GenerationRequestResponse:
    req = await _load_request(db, request_id, _owner(user))
    return await _request_response(db, req)


@router.get("/requests/{request_id}/events")
async def stream_request_events(
    request_id: str, user: dict = Depends(require_auth), db: AsyncSession = Depends(get_db)
) -> StreamingResponse:
    owner = _owner(user)
    await _load_request(db, request_id, owner)  # 404 before opening the stream
    return StreamingResponse(
        request_event_stream(request_id, owner),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


@router.get("/{moodboard_id}")
async def get_moodboard(
    moodboard_id: str, user: dict = Depends(require_auth), db: AsyncSession = Depends(get_db)
) -> MoodboardResponse:
    return _moodboard_response(await _load_moodboard(db, moodboard_id, _owner(user)))


@router.get("/{moodboard_id}/html", response_class=HTMLResponse)
async def get_moodboard_html(
    moodboard_id: str, user: dict = Depends(require_auth), db: AsyncSession = Depends(get_db)
) -> HTMLResponse:
    mb = await _load_moodboard(db, moodboard_id, _owner(user))
    if not mb.html:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="moodboard not ready")
    return HTMLResponse(content=mb.html)


@router.get("/{moodboard_id}/image/{index}")
async def get_moodboard_image(
    moodboard_id: str,
    index: int,
    user: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> Response:
    mb = await _load_moodboard(db, moodboard_id, _owner(user))
    ref = next((r for r in (mb.images or []) if r["index"] == index), None)
    if ref is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="image not found")
    try:
        data, content_type = await asyncio.to_thread(get_storage().get, ref["key"])
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="asset missing") from exc
    return Response(content=data, media_type=content_type)
