"""Briefing endpoints — the agentic, multi-step moodboard brief.

Usable entirely on its own (a client can brief without ever generating). Every route
is protected; sessions are scoped to the caller's ``sub``.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.auth import require_auth
from app.ids import new_id
from app.models.brief import BriefSession
from app.providers import get_llm
from app.schemas.brief import AnswerRequest, BriefContent, BriefSessionResponse
from app.services import briefing

router = APIRouter(prefix="/briefs", tags=["briefs"], dependencies=[Depends(require_auth)])


def _owner(claims: dict) -> str:
    return claims.get("sub") or "unknown"


def _response(session: BriefSession) -> BriefSessionResponse:
    content = BriefContent(**session.state)
    return BriefSessionResponse(
        id=session.id,
        status=session.status,
        next_question=briefing.current_question(content),
        content=content,
    )


async def _load_owned(db: AsyncSession, brief_id: str, owner: str) -> BriefSession:
    session = await db.get(BriefSession, brief_id)
    if session is None or session.owner != owner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="brief not found")
    return session


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_brief(
    user: dict = Depends(require_auth), db: AsyncSession = Depends(get_db)
) -> BriefSessionResponse:
    content = briefing.new_content()
    session = BriefSession(
        id=new_id(), owner=_owner(user), status="active", state=content.model_dump()
    )
    db.add(session)
    await db.commit()
    return _response(session)


@router.get("/{brief_id}")
async def get_brief(
    brief_id: str, user: dict = Depends(require_auth), db: AsyncSession = Depends(get_db)
) -> BriefSessionResponse:
    return _response(await _load_owned(db, brief_id, _owner(user)))


@router.post("/{brief_id}/answer")
async def answer_brief(
    brief_id: str,
    req: AnswerRequest,
    user: dict = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> BriefSessionResponse:
    session = await _load_owned(db, brief_id, _owner(user))
    content = BriefContent(**session.state)
    try:
        content = await briefing.submit_answer(content, get_llm(), req)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    session.state = content.model_dump()
    await db.commit()
    return _response(session)


@router.post("/{brief_id}/directions")
async def compose_brief_directions(
    brief_id: str, user: dict = Depends(require_auth), db: AsyncSession = Depends(get_db)
) -> BriefSessionResponse:
    session = await _load_owned(db, brief_id, _owner(user))
    content = briefing.compose_directions(BriefContent(**session.state))
    session.state = content.model_dump()
    session.status = "ready"
    await db.commit()
    return _response(session)
