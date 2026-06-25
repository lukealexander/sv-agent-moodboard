"""Client-side id generation for sessions, requests, moodboards, options, directions."""

import uuid


def new_id() -> str:
    """A UUID4 string — used for primary keys (String(36), portable across DBs)."""
    return str(uuid.uuid4())


def uid(prefix: str) -> str:
    """A short prefixed id for in-document objects (answer options, directions)."""
    return f"{prefix}-{uuid.uuid4().hex[:8]}"
