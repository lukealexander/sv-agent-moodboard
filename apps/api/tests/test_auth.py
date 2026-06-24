"""Authentication enforcement on protected routes.

These tests pin down the security contract of ``require_auth``:

* In **local dev** the auth check is bypassed entirely.
* In **production** a request must carry a valid, unexpired Cognito **access
  token** signed by a key in the JWKS and issued by *this pool* — anything else
  is a 401. Validation is POOL-scoped (issuer + signature + ``token_use``), not
  pinned to one app client, so a token from another service's client in the same
  pool is accepted (cross-service / api-to-api), unless an allow-list is set.

``/items`` stands in for "any protected route". The happy/failure paths use the
``cognito`` fixture's token factory (see ``conftest.py``) to exercise the real
validation code in ``app.dependencies.auth`` without touching the network.
"""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from tests.conftest import auth_header


# ── Local dev: auth bypassed ──────────────────────────────────────────────────


def test_protected_route_open_in_local_dev(client: TestClient, local_dev: None) -> None:
    """With LOCAL_DEV=true, protected endpoints are reachable without any token."""
    response = client.get("/items")
    assert response.status_code == 200


# ── Production: missing / malformed credentials are rejected ───────────────────


def test_missing_token_is_rejected(client: TestClient, production: None) -> None:
    response = client.get("/items")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_malformed_token_is_rejected(client: TestClient, production: None) -> None:
    """A string that isn't a well-formed JWT fails before any network call."""
    response = client.get("/items", headers=auth_header("not.a.real.token"))
    assert response.status_code == 401


# ── Production: cryptographic validation against the JWKS ──────────────────────


def test_valid_token_is_accepted(
    client: TestClient, cognito: Callable[..., str]
) -> None:
    """A properly signed, unexpired access token from this pool is accepted."""
    response = client.get("/items", headers=auth_header(cognito()))
    assert response.status_code == 200


def test_expired_token_is_rejected(
    client: TestClient, cognito: Callable[..., str]
) -> None:
    token = cognito(exp=0)  # expired in 1970
    response = client.get("/items", headers=auth_header(token))
    assert response.status_code == 401


def test_token_from_another_service_client_is_accepted(
    client: TestClient, cognito: Callable[..., str]
) -> None:
    """Pool-scoped validation: a token minted for a DIFFERENT app client in the
    same pool is accepted — this is what makes cross-service / api-to-api work."""
    token = cognito(client_id="some-other-service-client")
    response = client.get("/items", headers=auth_header(token))
    assert response.status_code == 200


def test_wrong_issuer_is_rejected(
    client: TestClient, cognito: Callable[..., str]
) -> None:
    """A token from a different user pool (issuer) must not be accepted."""
    token = cognito(iss="https://cognito-idp.eu-west-2.amazonaws.com/eu-west-2_OTHERPOOL")
    response = client.get("/items", headers=auth_header(token))
    assert response.status_code == 401


def test_id_token_is_rejected(
    client: TestClient, cognito: Callable[..., str]
) -> None:
    """Only access tokens may call the API; an id token (token_use=id) is a 401."""
    token = cognito(token_use="id")
    response = client.get("/items", headers=auth_header(token))
    assert response.status_code == 401


def test_client_id_allow_list_is_enforced_when_set(
    client: TestClient, cognito: Callable[..., str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """With COGNITO_ALLOWED_CLIENT_IDS set, a token whose client_id is not on the
    list is rejected, while a listed one is accepted (defense in depth)."""
    from app.config import settings

    monkeypatch.setattr(settings, "cognito_allowed_client_ids", "allowed-a, allowed-b")
    assert client.get("/items", headers=auth_header(cognito(client_id="intruder"))).status_code == 401
    assert client.get("/items", headers=auth_header(cognito(client_id="allowed-b"))).status_code == 200


def test_unknown_signing_key_is_rejected(
    client: TestClient, cognito: Callable[..., str]
) -> None:
    """A token whose `kid` isn't in the JWKS is rejected (forged/rotated key)."""
    token = cognito(kid="unknown-kid")
    response = client.get("/items", headers=auth_header(token))
    assert response.status_code == 401
