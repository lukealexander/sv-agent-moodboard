"""Migration 0002 and model registration for the moodboard tables."""

import pathlib
import sqlite3

import pytest
from alembic import command
from alembic.config import Config

from app.db.base import Base


@pytest.fixture
def db_file(tmp_path: pathlib.Path) -> pathlib.Path:
    return tmp_path / "moodboard_migrations.db"


@pytest.fixture
def alembic_cfg(db_file: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> Config:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    api_root = pathlib.Path(__file__).parent.parent
    cfg = Config(str(api_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(api_root / "alembic"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_file}")
    return cfg


def test_models_registered_on_metadata() -> None:
    import app.models  # noqa: F401 — triggers registration

    for table in ("brief_sessions", "generation_requests", "moodboards"):
        assert table in Base.metadata.tables


def test_upgrade_creates_moodboard_tables(alembic_cfg: Config, db_file: pathlib.Path) -> None:
    command.upgrade(alembic_cfg, "head")
    with sqlite3.connect(db_file) as conn:
        tables = {
            row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        gen_cols = {row[1] for row in conn.execute("PRAGMA table_info('generation_requests')")}
    assert {"brief_sessions", "generation_requests", "moodboards"} <= tables
    assert {"id", "owner", "brief_id", "input", "status"} <= gen_cols


def test_downgrade_removes_moodboard_tables(alembic_cfg: Config, db_file: pathlib.Path) -> None:
    command.upgrade(alembic_cfg, "head")
    command.downgrade(alembic_cfg, "base")
    with sqlite3.connect(db_file) as conn:
        tables = {
            row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    assert not ({"brief_sessions", "generation_requests", "moodboards"} & tables)
