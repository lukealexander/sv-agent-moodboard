"""Database layer: Alembic migrations and model registration.

The skeleton ships with the DB layer present but dormant (no DATABASE_URL needed to
run the API). These tests verify the migration machinery works end to end against a
throwaway SQLite file, and that every model is registered on ``Base.metadata`` so
Alembic autogenerate can see it.
"""

import pathlib
import sqlite3

import pytest
from alembic import command
from alembic.config import Config

from app.db.base import Base


@pytest.fixture
def db_file(tmp_path: pathlib.Path) -> pathlib.Path:
    return tmp_path / "test_migrations.db"


@pytest.fixture
def alembic_cfg(db_file: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> Config:
    # env.py reads DATABASE_URL from the environment; clear it so the SQLite URL
    # injected below via the Alembic Config is the one that's used.
    monkeypatch.delenv("DATABASE_URL", raising=False)
    api_root = pathlib.Path(__file__).parent.parent
    cfg = Config(str(api_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(api_root / "alembic"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_file}")
    return cfg


def test_upgrade_creates_expected_schema(
    alembic_cfg: Config, db_file: pathlib.Path
) -> None:
    """`upgrade head` builds the items table with the columns the model declares."""
    command.upgrade(alembic_cfg, "head")

    with sqlite3.connect(db_file) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info('items')")}
    assert columns == {"id", "name", "description"}


def test_downgrade_is_reversible(
    alembic_cfg: Config, db_file: pathlib.Path
) -> None:
    """`downgrade base` cleanly removes everything the migrations created."""
    command.upgrade(alembic_cfg, "head")
    command.downgrade(alembic_cfg, "base")

    with sqlite3.connect(db_file) as conn:
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    assert "items" not in tables


def test_item_model_is_registered_on_metadata() -> None:
    """Guards against `app/models/__init__.py` forgetting to import a model,
    which would silently hide it from Alembic autogenerate."""
    import app.models  # noqa: F401 — triggers registration

    assert "items" in Base.metadata.tables
