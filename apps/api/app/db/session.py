from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

# Engine is only created when DATABASE_URL is set.
_engine = None
_session_factory = None


def _get_engine():
    global _engine, _session_factory
    if _engine is None:
        if not settings.database_url:
            raise RuntimeError("DATABASE_URL is not configured")
        _engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine, _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    _, factory = _get_engine()
    async with factory() as session:
        yield session


async def check_connection() -> None:
    """Open a connection and run a trivial query to confirm the database is reachable.

    Raises ``RuntimeError`` if ``DATABASE_URL`` is not configured, or a SQLAlchemy /
    driver error if the database can't be reached. Used by the ``/health/db``
    readiness probe.
    """
    engine, _ = _get_engine()
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
