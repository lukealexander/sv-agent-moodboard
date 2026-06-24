"""Health endpoints: the public, unauthenticated probes.

``/health`` is the liveness probe used by the ECS/ALB health check and the frontend
dashboard's heartbeat card. It must never require auth, must return a stable,
machine-readable shape, and must NOT depend on the database.

``/health/db`` is the separate readiness probe that reports database connectivity for
the dashboard.
"""

import pathlib

import pytest
from fastapi.testclient import TestClient

import app.db.session as session_module
from app.config import settings
from app.routers import health as health_router


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_requires_no_auth_in_production(
    client: TestClient, production: None
) -> None:
    """Even with auth enforced, /health must stay open (it's the load-balancer probe)."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_db_disabled_when_no_database_url(client: TestClient) -> None:
    """With no DATABASE_URL the DB layer is dormant — report 'disabled', not an error."""
    assert settings.database_url == ""  # the suite boots without a DB configured
    response = client.get("/health/db")
    assert response.status_code == 200
    assert response.json() == {"status": "disabled"}


def test_health_db_ok_when_reachable(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """A reachable database answers SELECT 1, so the probe reports 'ok'."""
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'probe.db'}"
    monkeypatch.setattr(settings, "database_url", db_url)
    # Reset the lazily-built engine cache so the SQLite URL above is the one used.
    monkeypatch.setattr(session_module, "_engine", None)
    monkeypatch.setattr(session_module, "_session_factory", None)

    response = client.get("/health/db")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_db_reports_error_when_unreachable(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A configured-but-unreachable database surfaces as 503 with a safe detail."""
    monkeypatch.setattr(settings, "database_url", "postgresql+asyncpg://u:p@db:5432/x")

    async def boom() -> None:
        raise ConnectionRefusedError("connection refused")

    monkeypatch.setattr(health_router, "check_connection", boom)

    response = client.get("/health/db")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "error"
    # Only the exception class name is exposed — never the message/connection string.
    assert body["detail"] == "ConnectionRefusedError"
