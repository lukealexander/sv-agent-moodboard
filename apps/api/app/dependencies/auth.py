import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwk, jwt

from app.config import settings

security = HTTPBearer(auto_error=False)

# Module-level JWKS cache — populated on first request
_jwks: dict | None = None


async def _get_jwks() -> dict:
    global _jwks
    if _jwks is None:
        async with httpx.AsyncClient() as client:
            resp = await client.get(settings.cognito_jwks_url)
            resp.raise_for_status()
            _jwks = resp.json()
    return _jwks


def _find_key(kid: str, jwks: dict) -> dict:
    for key in jwks.get("keys", []):
        if key["kid"] == kid:
            return key
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown signing key")


async def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict:
    """Validate a Cognito **access token** at the POOL level.

    We verify the signature against the pool's JWKS and the ``iss`` claim against
    the pool issuer, then require ``token_use == "access"``. We deliberately do
    NOT pin the audience/app-client to a single id: every service has its own app
    client in the shared pool, so binding to one id would reject legitimate
    cross-service and api-to-api calls. Set ``COGNITO_ALLOWED_CLIENT_IDS`` to
    restrict to a known set of clients (defense in depth). Authorize downstream on
    the caller's identity (``sub``) and ``scope``.

    In LOCAL_DEV mode this returns a stub user without validation.
    """
    if settings.local_dev:
        return {"sub": "local-dev-user", "email": "dev@local"}

    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    token = credentials.credentials
    try:
        headers = jwt.get_unverified_headers(token)
        jwks = await _get_jwks()
        raw_key = _find_key(headers["kid"], jwks)
        public_key = jwk.construct(raw_key)
        # Verify signature + expiry + issuer. Audience is not checked: Cognito
        # access tokens carry no `aud` claim, and validation is pool-scoped.
        claims = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            issuer=settings.cognito_issuer,
            options={"verify_aud": False},
        )
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    # Only access tokens may call the API (id tokens are for the frontend).
    if claims.get("token_use") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not an access token"
        )

    # Optional allow-list of app clients permitted to call this API.
    allowed = settings.cognito_allowed_client_id_list
    if allowed and claims.get("client_id") not in allowed:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Client not allowed"
        )

    return claims


async def fetch_userinfo(access_token: str) -> dict:
    """Fetch the caller's profile (email, name, ...) from Cognito's OIDC userInfo
    endpoint, authenticated by their own access token.

    Cognito access tokens deliberately omit profile claims like ``email`` (those
    live in the id token). The userInfo endpoint returns them for whatever the
    token's ``scope`` grants — so the token must have been issued with ``email``
    / ``profile`` for this to populate.

    Best-effort: returns ``{}`` when the domain is unconfigured or the call fails,
    so identity enrichment never turns a valid request into an error.
    """
    if not settings.cognito_domain:
        return {}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                settings.cognito_userinfo_url,
                headers={"Authorization": f"Bearer {access_token}"},
            )
        if resp.status_code != 200:
            return {}
        return resp.json()
    except httpx.HTTPError:
        return {}


async def require_user(
    claims: dict = Depends(require_auth),
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict:
    """Validated access-token claims, enriched with the caller's profile.

    Use this for routes that need the caller's identity (email/name); use
    ``require_auth`` when authorization (sub/scope/groups) is all you need — it
    skips the extra userInfo round-trip.

    The validated claims always win on conflict; userInfo only *adds* missing
    profile fields. In LOCAL_DEV the stub user already carries an email, so we
    short-circuit without a network call.
    """
    if settings.local_dev:
        return claims

    token = credentials.credentials if credentials else None
    profile = await fetch_userinfo(token) if token else {}
    return {**profile, **claims}
