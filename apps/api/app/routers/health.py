"""Health probes — public and unauthenticated.

``/health`` is the liveness probe used by the ALB / ECS health check. It must stay
cheap and must NOT depend on the database: coupling it to the DB would let a
transient database blip fail the probe and take every API task down with it.

``/health/db`` is a separate readiness probe that reports database connectivity for
the dashboard. It is deliberately independent of ``/health`` so the DB's state never
affects the liveness signal.
"""

from fastapi import APIRouter, Response, status

from app.config import settings
from app.db.session import check_connection

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/health/db")
async def health_db(response: Response) -> dict:
    """Report database connectivity.

    * ``{"status": "disabled"}`` — no ``DATABASE_URL`` configured (the DB layer is
      dormant; this is the skeleton's default, not an error).
    * ``{"status": "ok"}`` — a ``SELECT 1`` succeeded.
    * ``{"status": "error", "detail": ...}`` with HTTP 503 — configured but
      unreachable. ``detail`` is the exception class name only; the full message is
      withheld to avoid leaking connection internals on this public endpoint.
    """
    if not settings.database_url:
        return {"status": "disabled"}
    try:
        await check_connection()
    except Exception as exc:  # noqa: BLE001 — any failure means "unreachable"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "error", "detail": type(exc).__name__}
    return {"status": "ok"}
