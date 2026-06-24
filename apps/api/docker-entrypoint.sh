#!/bin/sh
# Container entrypoint for the production API image.
#
# Applies database migrations BEFORE the app starts serving, so every rollout
# brings the schema to head as part of the normal ECS deploy — no separate
# Fargate migration task on the hot path. With desired_count = 1 only the new
# task runs this per deploy; at >1 replica, concurrent runners are serialized by
# the Postgres advisory lock in alembic/env.py (do_run_migrations).
#
# Behaviour:
#   * DATABASE_URL set   -> run `alembic upgrade head`, then exec the CMD.
#                           A migration failure aborts startup (set -e), so the
#                           container never becomes healthy and the ECS circuit
#                           breaker rolls the deploy back instead of serving an
#                           unmigrated schema.
#   * DATABASE_URL unset -> skip migrations (stateless mode, and also the one-shot
#                           bootstrap task, which sets DB_* but not DATABASE_URL
#                           and runs its own migrations via app.dbtask).
set -eu

if [ -n "${DATABASE_URL:-}" ]; then
  echo "[entrypoint] applying migrations: alembic upgrade head"
  uv run alembic upgrade head
  echo "[entrypoint] migrations complete"
else
  echo "[entrypoint] DATABASE_URL not set — skipping migrations"
fi

exec "$@"
