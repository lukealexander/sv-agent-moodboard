import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.db.base import Base
import app.models  # noqa: F401 — ensure all models are imported for autogenerate

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Read the connection URL straight from DATABASE_URL rather than app.config.
# Migrations only need a URL; importing the app's Settings would impose the full
# production config contract (CORS, Cognito, ...) on contexts that never serve
# HTTP — notably the one-shot db bootstrap task (app/dbtask.py), which sets
# DATABASE_URL and then runs `alembic upgrade head`.
# Only override when set, so tests can inject their own URL (e.g. a throwaway
# SQLite file) via the Alembic Config without an empty value clobbering it.
# % is doubled because Config is backed by a ConfigParser, which performs
# %-interpolation on read — a literal % (e.g. in a password) otherwise raises
# InterpolationSyntaxError the moment get_section/get_main_option reads it back.
database_url = os.environ.get("DATABASE_URL", "")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        # Serialize concurrent migrators (e.g. multiple API replicas running
        # `alembic upgrade head` on startup at once) so only one applies a given
        # revision; the rest block here, then find nothing to do. xact-scoped, so
        # it's auto-released on commit/rollback/disconnect — a crashed task can't
        # leave it held. Postgres-only; a no-op under the SQLite test suite.
        if connection.dialect.name == "postgresql":
            connection.exec_driver_sql("SELECT pg_advisory_xact_lock(8274013)")
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
