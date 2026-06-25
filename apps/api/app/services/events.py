"""Server-Sent Events for generation progress.

Streams a status snapshot whenever it changes and closes on a terminal request
status. Reads the DB each tick, so it reflects progress regardless of which worker /
instance is running the job (the in-process ``BackgroundTasks`` worker writes the same
rows). For multi-instance durability a shared broker (e.g. Redis pub/sub) would
replace the poll loop — noted in TODO.
"""

import asyncio
import json
from collections.abc import AsyncGenerator

from sqlalchemy import select

from app.db.session import session_scope
from app.models.moodboard import GenerationRequest, Moodboard

_TERMINAL = {"done", "partial", "error"}
_MAX_TICKS = 600  # ~10 minutes safety cap


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj)}\n\n"


async def request_event_stream(request_id: str, owner: str) -> AsyncGenerator[str, None]:
    last: str | None = None
    for _ in range(_MAX_TICKS):
        async with session_scope() as db:
            req = await db.get(GenerationRequest, request_id)
            if req is None or req.owner != owner:
                yield _sse({"type": "error", "detail": "request not found"})
                return
            rows = (
                await db.execute(select(Moodboard).where(Moodboard.request_id == request_id))
            ).scalars().all()
            snapshot = {
                "type": "status",
                "request": req.status,
                "moodboards": [
                    {"id": m.id, "direction": m.direction_name, "status": m.status} for m in rows
                ],
            }
        payload = json.dumps(snapshot, sort_keys=True)
        if payload != last:
            last = payload
            yield _sse(snapshot)
        if snapshot["request"] in _TERMINAL:
            yield _sse({"type": "done", "request": snapshot["request"]})
            return
        await asyncio.sleep(1.0)
    yield _sse({"type": "timeout"})
