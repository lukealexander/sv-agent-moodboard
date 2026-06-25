"""Persisted moodboard brief sessions.

A brief session is the server-side state of a multi-step briefing conversation:
the answered stages, any forks, and the curated directions. The full content lives
in ``state`` as JSON (portable across Postgres and the SQLite test DB); see
``app.schemas.brief.BriefContent`` for its shape. Persisting it lets a session be
revisited or handed to generation later.
"""

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BriefSession(Base):
    __tablename__ = "brief_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    # active | ready (directions composed) — a session is usable for generation once "ready".
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    state: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )
