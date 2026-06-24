"""One-shot database bootstrap task.

Runs as a short-lived Fargate task (see ``terraform/modules/db``) — NEVER as part
of the long-running API. ``scripts/deploy.sh`` launches it with ``aws ecs run-task``
for FIRST-TIME provisioning (when the DATABASE_URL secret is still empty) or on
demand via ``FORCE_DB_BOOTSTRAP=1``. It is fully idempotent. Routine schema
migrations are NOT done here — the API applies ``alembic upgrade head`` on startup
(``apps/api/docker-entrypoint.sh``), so deploys skip this slow task once the
service is provisioned. This task still runs migrations too (step 4), so the very
first deploy comes up fully migrated before the API rolls out.

What it does, connecting to the shared RDS instance as the master user (whose
credentials it reads from Secrets Manager via the scoped bootstrap task role):

  1. Create this service's login role ``<service>_user`` (or align its password).
  2. Create the database ``<service>`` it owns.
  3. Write the ``postgresql+asyncpg://…`` connection string into this service's
     Secrets Manager secret — the value the api module injects as ``DATABASE_URL``.
     The password is generated on first run and REUSED on later deploys (read
     back from the secret) so redeploys don't churn the credential.
  4. Run ``alembic upgrade head``.

The master credential is read here and never reaches the running service, which
only ever sees its own least-privilege ``DATABASE_URL``.

Configuration is entirely via environment variables set by the task definition:
``DB_HOST``, ``DB_PORT``, ``DB_NAME``, ``DB_USER``, ``MASTER_SECRET_ARN``,
``DB_URL_SECRET_ARN`` and ``AWS_REGION`` (``AWS_DEFAULT_REGION``).
"""

from __future__ import annotations

import json
import os
import secrets
import sys
import urllib.parse

import boto3
import psycopg2
from psycopg2 import sql


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        sys.exit(f"[dbtask] ERROR: missing required environment variable: {name}")
    return value


def _get_secret_string(client, arn: str) -> str:
    return client.get_secret_value(SecretId=arn)["SecretString"]


def _reuse_password(client, arn: str) -> str | None:
    """Return the password already stored in the service secret, if any.

    Reusing it keeps the credential stable across deploys. Returns ``None`` when
    the secret has never been populated or doesn't parse as our URL, in which
    case the caller generates a fresh password.
    """
    try:
        current = _get_secret_string(client, arn)
    except client.exceptions.ResourceNotFoundException:
        return None
    if not current:
        return None
    try:
        parsed = urllib.parse.urlparse(current)
    except ValueError:
        return None
    if parsed.password:
        return urllib.parse.unquote(parsed.password)
    return None


def _connect_master(host: str, port: str, master_user: str, master_password: str):
    """Open an autocommit connection to the ``postgres`` maintenance database as the
    master user. autocommit is required because ``CREATE``/``DROP DATABASE`` cannot
    run inside a transaction block. Shared by provisioning and teardown.
    """
    conn = psycopg2.connect(
        host=host,
        port=port,
        dbname="postgres",
        user=master_user,
        password=master_password,
        sslmode="require",
        connect_timeout=15,
    )
    conn.autocommit = True
    return conn


def _provision(host: str, port: str, db_name: str, db_user: str, password: str,
               master_user: str, master_password: str, *, is_first_provision: bool) -> None:
    """Idempotently create the login role and the database it owns.

    On this service's FIRST provision (its secret holds no password yet) the role and
    database must NOT already exist. If they do, another service derived the same name,
    or a previous teardown dropped the secret without dropping the database — adopting
    it would share data and reset the other owner's password, so we fail loudly instead.
    Re-runs (the secret already holds a password) align the role password and skip the
    existing database, as before.
    """
    conn = _connect_master(host, port, master_user, master_password)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (db_user,))
            role_exists = cur.fetchone() is not None
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
            db_exists = cur.fetchone() is not None

            if is_first_provision and (role_exists or db_exists):
                existing = " and ".join(
                    label
                    for label, present in (
                        (f"role {db_user!r}", role_exists),
                        (f"database {db_name!r}", db_exists),
                    )
                    if present
                )
                sys.exit(
                    f"[dbtask] ERROR: {existing} already exists on the shared RDS, but "
                    f"this service has no stored credential yet (first-time provision). "
                    f"Another service may own this name, or a previous teardown removed "
                    f"the secret without dropping the database. Refusing to adopt it — "
                    f"choose a unique service_name, set db_name/db_user explicitly, or "
                    f"drop the stale objects with scripts/teardown-db.sh."
                )

            if role_exists:
                cur.execute(
                    sql.SQL("ALTER ROLE {} WITH LOGIN PASSWORD %s").format(
                        sql.Identifier(db_user)
                    ),
                    (password,),
                )
                print(f"[dbtask] role {db_user!r} already exists — password aligned")
            else:
                cur.execute(
                    sql.SQL("CREATE ROLE {} WITH LOGIN PASSWORD %s").format(
                        sql.Identifier(db_user)
                    ),
                    (password,),
                )
                print(f"[dbtask] created role {db_user!r}")

            if db_exists:
                print(f"[dbtask] database {db_name!r} already exists")
            else:
                # No IF NOT EXISTS for CREATE DATABASE; guarded by the check above.
                cur.execute(
                    sql.SQL("CREATE DATABASE {} OWNER {}").format(
                        sql.Identifier(db_name), sql.Identifier(db_user)
                    )
                )
                print(f"[dbtask] created database {db_name!r} owned by {db_user!r}")
    finally:
        conn.close()


def _run_migrations(database_url: str) -> None:
    """Run ``alembic upgrade head`` against the service database.

    alembic's ``env.py`` reads the URL from ``settings.database_url`` (i.e. the
    ``DATABASE_URL`` env var), so set it before importing/invoking alembic.
    """
    os.environ["DATABASE_URL"] = database_url

    from alembic import command
    from alembic.config import Config

    api_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg = Config(os.path.join(api_root, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(api_root, "alembic"))

    print("[dbtask] running `alembic upgrade head`...")
    command.upgrade(cfg, "head")
    print("[dbtask] migrations complete")


def main() -> None:
    host = _require_env("DB_HOST")
    port = _require_env("DB_PORT")
    db_name = _require_env("DB_NAME")
    db_user = _require_env("DB_USER")
    master_arn = _require_env("MASTER_SECRET_ARN")
    url_arn = _require_env("DB_URL_SECRET_ARN")
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")

    sm = boto3.client("secretsmanager", region_name=region)

    # RDS-managed master secret is JSON: {"username": ..., "password": ...}.
    master = json.loads(_get_secret_string(sm, master_arn))
    master_user = master["username"]
    master_password = master["password"]

    # No stored password => this service's secret has never been written => first
    # provision. The guard in _provision uses this to refuse adopting a pre-existing
    # role/database (another service's, or a stale leftover after teardown).
    reused_password = _reuse_password(sm, url_arn)
    password = reused_password or secrets.token_urlsafe(24)

    _provision(
        host, port, db_name, db_user, password, master_user, master_password,
        is_first_provision=reused_password is None,
    )

    # Password is percent-encoded so any URL-special characters survive parsing.
    encoded_password = urllib.parse.quote(password, safe="")
    database_url = (
        f"postgresql+asyncpg://{db_user}:{encoded_password}@{host}:{port}/{db_name}"
    )
    sm.put_secret_value(SecretId=url_arn, SecretString=database_url)
    print(f"[dbtask] wrote DATABASE_URL secret for database {db_name!r}")

    _run_migrations(database_url)
    print("[dbtask] done")


if __name__ == "__main__":
    main()
