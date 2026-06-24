"""Shared pytest fixtures for the API test suite.

Two execution modes are exercised:

* **local dev** (``LOCAL_DEV=true``) — ``require_auth`` returns a stub user and no
  token is validated. This is the default the test process boots in.
* **production** — ``LOCAL_DEV=false`` with Cognito configured. Tokens are validated
  against a JWKS. To keep the suite hermetic (no network, no real Cognito) we mint a
  throwaway RSA keypair, build a JWKS from its public half, and pre-populate the
  module-level JWKS cache. The ``make_token`` factory then signs tokens that the real
  validation code in ``app.dependencies.auth`` accepts or rejects.

The single ``settings`` object is shared by every module that did
``from app.config import settings``, so mutating it via ``monkeypatch.setattr`` (rather
than reloading modules) flips auth behaviour everywhere at once and is automatically
reverted at the end of each test.
"""

import os
import time
from collections.abc import Callable

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jose import jwk, jwt
from jose.constants import ALGORITHMS

# Boot the app in local-dev mode so importing it never requires real Cognito.
os.environ.setdefault("LOCAL_DEV", "true")

import app.dependencies.auth as auth_module  # noqa: E402
from app.config import settings as app_settings  # noqa: E402
from app.main import app  # noqa: E402

TEST_CLIENT_ID = "test-client-id"
TEST_USER_POOL_ID = "eu-west-2_TESTPOOL"
TEST_REGION = "eu-west-2"
TEST_KID = "test-key-1"
TEST_ISSUER = f"https://cognito-idp.{TEST_REGION}.amazonaws.com/{TEST_USER_POOL_ID}"


@pytest.fixture
def client() -> TestClient:
    """A TestClient that surfaces HTTP error responses instead of re-raising."""
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture
def local_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force LOCAL_DEV=true (the auth-bypass path)."""
    monkeypatch.setattr(app_settings, "local_dev", True)


@pytest.fixture
def production(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force production auth: LOCAL_DEV=false with Cognito configured.

    Also clears the JWKS cache so it can't leak between tests.
    """
    monkeypatch.setattr(app_settings, "local_dev", False)
    monkeypatch.setattr(app_settings, "cognito_user_pool_id", TEST_USER_POOL_ID)
    monkeypatch.setattr(app_settings, "cognito_region", TEST_REGION)
    monkeypatch.setattr(app_settings, "cognito_allowed_client_ids", "")
    monkeypatch.setattr(auth_module, "_jwks", None)


@pytest.fixture(scope="session")
def _rsa_keypair() -> tuple[str, str]:
    """A throwaway RSA keypair as (private_pem, public_pem). Session-scoped: keygen is slow."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    from cryptography.hazmat.primitives import serialization

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return private_pem, public_pem


@pytest.fixture
def cognito(
    production: None,
    monkeypatch: pytest.MonkeyPatch,
    _rsa_keypair: tuple[str, str],
) -> Callable[..., str]:
    """Production auth wired to a fake Cognito JWKS, returning a token factory.

    Builds a JWKS from the test public key and primes the module-level cache so
    ``require_auth`` never makes a network call. The returned ``make_token`` mints
    signed RS256 **access** tokens (the kind the SPA sends to the API); pass
    overrides to forge expired, wrong-issuer, id-token, or other-client tokens.
    """
    private_pem, public_pem = _rsa_keypair

    public_jwk = jwk.construct(public_pem, ALGORITHMS.RS256).to_dict()
    public_jwk["kid"] = TEST_KID
    monkeypatch.setattr(auth_module, "_jwks", {"keys": [public_jwk]})

    def make_token(*, kid: str = TEST_KID, **overrides: object) -> str:
        now = int(time.time())
        # Shape of a Cognito ACCESS token: pool issuer, token_use=access,
        # client_id (not aud), scope. No email — that lives in the id token.
        claims: dict = {
            "sub": "user-123",
            "username": "user-123",
            "iss": TEST_ISSUER,
            "client_id": TEST_CLIENT_ID,
            "scope": "openid email profile",
            "token_use": "access",
            "iat": now,
            "exp": now + 3600,
        }
        claims.update(overrides)
        return jwt.encode(claims, private_pem, algorithm="RS256", headers={"kid": kid})

    return make_token


def auth_header(token: str) -> dict[str, str]:
    """Convenience: build an Authorization header from a bare token."""
    return {"Authorization": f"Bearer {token}"}
