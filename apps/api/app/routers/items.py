"""Example protected resource.

Demonstrates the "protected by default" pattern: ``require_auth`` is declared
once at the router level so *every* route here rejects unauthenticated requests.
Handlers that need the caller's identity re-declare ``Depends(require_auth)`` as a
parameter — FastAPI caches the dependency within a request, so it runs only once.

Replace the hard-coded stubs with real database queries using ``get_db``.
"""

from fastapi import APIRouter, Depends

from app.dependencies.auth import require_auth

router = APIRouter(prefix="/items", tags=["items"], dependencies=[Depends(require_auth)])


@router.get("")
async def list_items(user: dict = Depends(require_auth)) -> list[dict]:
    # Replace with a real DB query: `async with get_db() as db: ...`
    return [{"id": 1, "name": "Example item", "description": "Replace with DB query"}]


@router.get("/{item_id}")
async def get_item(item_id: int, user: dict = Depends(require_auth)) -> dict:
    return {"id": item_id, "name": "Example item", "description": "Replace with DB query"}
