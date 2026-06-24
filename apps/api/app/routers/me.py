"""'Who am I' endpoint — returns the authenticated caller's identity.

This is the canonical example of a protected route that *uses* the result of
``require_user``. In production the returned object is the decoded set of Cognito
access-token claims, enriched with the caller's profile (email, ...) from the
userInfo endpoint; in local dev it is the stub user produced by ``require_auth``.
"""

from fastapi import APIRouter, Depends

from app.dependencies.auth import require_user

router = APIRouter(tags=["me"])


@router.get("/whoami")
async def whoami(user: dict = Depends(require_user)) -> dict:
    """Return the caller's identity derived from their bearer token."""
    return {
        "sub": user.get("sub"),
        "email": user.get("email"),
        "claims": user,
    }
