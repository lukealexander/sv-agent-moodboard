"""Persisted moodboard generation requests and their resulting moodboards.

A ``GenerationRequest`` is one call to generate from a brief; it fans out to one
``Moodboard`` per chosen direction. Requests and moodboards are persisted (not just
held in memory) so a slow or failed async generation can be polled/streamed and the
result revisited later.
"""

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class GenerationRequest(Base):
    __tablename__ = "generation_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    # Nullable: generation can run from a standalone brief payload with no saved session.
    brief_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    # The resolved generation plan the async worker reads:
    # {"brief_text": str, "directions": [{"name": str, "notes": [str]}]}.
    input: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # queued | running | done | partial | error
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )


class Moodboard(Base):
    __tablename__ = "moodboards"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    owner: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    direction_name: Mapped[str] = mapped_column(String(255), nullable=False)
    # queued | composing | rendering | assembling | done | error
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    # The agent-authored concept (title, summary, notes) — JSON.
    concept: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Ordered list of {hex, name} swatches.
    palette: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # Ordered list of {key, prompt, alt, content_type} for the rendered tiles.
    images: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # The self-contained shareable HTML (images inlined as data URIs).
    html: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )
