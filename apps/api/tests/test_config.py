"""Settings validation — focused on the CORS configuration contract.

Production must declare its allowed origins explicitly: the template refuses to boot
with `LOCAL_DEV=false` and no `CORS_ALLOWED_ORIGINS`, rather than silently falling back
to a wildcard (which would also be incompatible with credentialed requests).

These tests construct `Settings` directly with explicit kwargs (which override the
process environment), so they're independent of how the test process was launched.
"""

import pytest
from pydantic import ValidationError

from app.config import Settings


def test_local_dev_defaults_to_wildcard_origins() -> None:
    """In local dev an empty allow-list is fine and resolves to `*`."""
    settings = Settings(local_dev=True, cors_allowed_origins="")
    assert settings.cors_origins == ["*"]


def test_production_requires_explicit_origins() -> None:
    """With auth enforced, booting without CORS_ALLOWED_ORIGINS is a hard error."""
    with pytest.raises(ValidationError):
        Settings(local_dev=False, cors_allowed_origins="")


def test_production_parses_comma_separated_origins() -> None:
    settings = Settings(
        local_dev=False,
        cors_allowed_origins="https://app.example.com, https://www.example.com",
    )
    assert settings.cors_origins == [
        "https://app.example.com",
        "https://www.example.com",
    ]


def test_cognito_issuer_is_derived_from_pool_and_region() -> None:
    """The issuer the API validates `iss` against is built from pool id + region."""
    settings = Settings(
        local_dev=True,
        cognito_user_pool_id="eu-west-2_ABC123",
        cognito_region="eu-west-2",
    )
    assert settings.cognito_issuer == "https://cognito-idp.eu-west-2.amazonaws.com/eu-west-2_ABC123"
    # JWKS URL hangs off the same issuer.
    assert settings.cognito_jwks_url == (
        "https://cognito-idp.eu-west-2.amazonaws.com/eu-west-2_ABC123/.well-known/jwks.json"
    )


def test_allowed_client_ids_parse_to_list() -> None:
    """The optional app-client allow-list is comma-separated; empty = no list."""
    assert Settings(local_dev=True, cognito_allowed_client_ids="").cognito_allowed_client_id_list == []
    assert Settings(
        local_dev=True, cognito_allowed_client_ids="a, b ,c"
    ).cognito_allowed_client_id_list == ["a", "b", "c"]
