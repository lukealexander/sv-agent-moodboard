"""One-shot database teardown task — the inverse of ``app.dbtask``.

Drops this service's database and login role from the shared RDS instance. The
role + database are NOT in Terraform state (the bootstrap task creates them with
raw SQL), so ``terraform destroy`` leaves them behind, orphaned, on the shared
instance. Run this FIRST to remove them cleanly, then ``terraform destroy`` the
plumbing (secret, bootstrap role, log group, task definition).

It runs as a short-lived Fargate task — ``scripts/teardown-db.sh`` launches it by
reusing the db module's bootstrap task definition with the container command
overridden to ``python -m app.dbteardown`` (so it inherits the same DB_* env, the
master-secret access, and the in-VPC network path). NEVER part of the running API.

DESTRUCTIVE and irreversible. As a backstop against accidental runs it refuses to
do anything unless ``CONFIRM_TEARDOWN`` is set — ``scripts/teardown-db.sh`` sets it
only after the operator confirms. It only ever touches the identifiers passed via
``DB_NAME`` / ``DB_USER`` (this service's), never a wildcard.

Configuration via environment variables (a subset of what app.dbtask reads, set by
the same task definition): ``DB_HOST``, ``DB_PORT``, ``DB_NAME``, ``DB_USER``,
``MASTER_SECRET_ARN`` and ``AWS_REGION`` (``AWS_DEFAULT_REGION``).
"""

from __future__ import annotations

import json
import os
import sys

import boto3
from psycopg2 import sql

# Reuse the master-connection and secret helpers so provision/teardown stay in sync.
from app.dbtask import _connect_master, _get_secret_string, _require_env


def _teardown(host: str, port: str, db_name: str, db_user: str,
              master_user: str, master_password: str) -> None:
    """Drop the database then the role, as the master user. Idempotent: missing
    objects are skipped, so re-running after a partial teardown is safe.

    Order matters — a role can't be dropped while it still owns a database, so the
    database goes first. ``DROP DATABASE ... WITH (FORCE)`` terminates lingering
    connections (e.g. a still-running API task) so the drop doesn't block; it needs
    PostgreSQL 13+ (the shared RDS is well past that).
    """
    conn = _connect_master(host, port, master_user, master_password)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
            if cur.fetchone():
                cur.execute(
                    sql.SQL("DROP DATABASE {} WITH (FORCE)").format(
                        sql.Identifier(db_name)
                    )
                )
                print(f"[dbteardown] dropped database {db_name!r}")
            else:
                print(f"[dbteardown] database {db_name!r} does not exist — skipping")

            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (db_user,))
            if cur.fetchone():
                # The role owned only its (now-dropped) database, so DROP ROLE is
                # clean. If it fails, the role has lingering grants/objects elsewhere
                # — surfaced as a non-zero exit for the operator to resolve.
                cur.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(db_user)))
                print(f"[dbteardown] dropped role {db_user!r}")
            else:
                print(f"[dbteardown] role {db_user!r} does not exist — skipping")
    finally:
        conn.close()


def main() -> None:
    if not os.environ.get("CONFIRM_TEARDOWN"):
        sys.exit(
            "[dbteardown] ERROR: refusing to run without CONFIRM_TEARDOWN set "
            "(scripts/teardown-db.sh sets it after the operator confirms)."
        )

    host = _require_env("DB_HOST")
    port = _require_env("DB_PORT")
    db_name = _require_env("DB_NAME")
    db_user = _require_env("DB_USER")
    master_arn = _require_env("MASTER_SECRET_ARN")
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")

    sm = boto3.client("secretsmanager", region_name=region)
    master = json.loads(_get_secret_string(sm, master_arn))

    print(f"[dbteardown] dropping database {db_name!r} and role {db_user!r} on {host}...")
    _teardown(host, port, db_name, db_user, master["username"], master["password"])
    print("[dbteardown] done")


if __name__ == "__main__":
    main()
