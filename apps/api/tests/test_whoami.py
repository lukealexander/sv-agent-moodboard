"""The /whoami endpoint — surfaces the authenticated caller's identity.

Demonstrates a protected route that *consumes* the claims returned by
``require_auth``: in local dev that's a stub user; in production it's the decoded
Cognito JWT claims.
"""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

import app.dependencies.auth as auth_module
from tests.conftest import auth_header


def test_whoami_returns_stub_user_in_local_dev(
    client: TestClient, local_dev: None
) -> None:
    response = client.get("/whoami")
    assert response.status_code == 200
    body = response.json()
    assert body["sub"] == "local-dev-user"
    assert body["email"] == "dev@local"


def test_whoami_requires_auth_in_production(
    client: TestClient, production: None
) -> None:
    response = client.get("/whoami")
    assert response.status_code == 401


def test_whoami_reflects_token_claims_in_production(
    client: TestClient, cognito: Callable[..., str]
) -> None:
    token = cognito(sub="abc-789")
    response = client.get("/whoami", headers=auth_header(token))
    assert response.status_code == 200

    body = response.json()
    assert body["sub"] == "abc-789"
    # The access token carries no email claim, and COGNITO_DOMAIN is unset in the
    # production fixture, so userInfo enrichment is skipped and email is None.
    assert body["email"] is None
    # The full claim set is echoed under "claims".
    assert body["claims"]["token_use"] == "access"
    assert body["claims"]["client_id"] == "test-client-id"


def test_whoami_enriches_email_from_userinfo(
    client: TestClient,
    cognito: Callable[..., str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the userInfo endpoint resolves, /whoami surfaces the caller's email.

    We stub ``fetch_userinfo`` (no real Cognito domain in tests) to confirm the
    profile is merged into the validated access-token claims, while the validated
    claims still win on any overlapping key.
    """

    async def fake_userinfo(_token: str) -> dict:
        return {"sub": "SHOULD-NOT-WIN", "email": "alice@example.com"}

    monkeypatch.setattr(auth_module, "fetch_userinfo", fake_userinfo)

    token = cognito(sub="user-123")
    response = client.get("/whoami", headers=auth_header(token))
    assert response.status_code == 200

    body = response.json()
    assert body["email"] == "alice@example.com"
    # Validated claim wins over the userInfo value for overlapping keys.
    assert body["sub"] == "user-123"
    assert body["claims"]["email"] == "alice@example.com"
