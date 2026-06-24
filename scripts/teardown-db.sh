#!/usr/bin/env bash
# Usage: [AWS_REGION=eu-west-2] [FORCE_TEARDOWN=1] ./scripts/teardown-db.sh [--yes]
#
# Drops THIS service's database + login role from the shared RDS instance — the
# inverse of the bootstrap task. Those objects are created with raw SQL and are
# NOT in Terraform state, so `terraform destroy` would otherwise leave them behind
# orphaned on the shared instance. Run this BEFORE `terraform destroy`.
#
# It launches a one-shot Fargate task that reuses the db module's bootstrap task
# definition with the container command overridden to `python -m app.dbteardown`
# (inheriting the same DB_* env, master-secret access, and in-VPC network path).
#
# DESTRUCTIVE and irreversible. By default it prints exactly what it will drop and
# requires you to TYPE THE DATABASE NAME to confirm. Pass --yes (or FORCE_TEARDOWN=1)
# to skip the prompt in CI.
#
# Prerequisites (same as deploy.sh):
#   - AWS credentials configured (env vars / SSO / ~/.aws)
#   - aws-cli + terraform on PATH
#   - terraform/backend.tf and terraform/terraform.tfvars present

set -euo pipefail

AWS_REGION="${AWS_REGION:-eu-west-2}"
ASSUME_YES="${FORCE_TEARDOWN:-}"

for arg in "$@"; do
  case "$arg" in
    --yes|-y) ASSUME_YES=1 ;;
    *) echo "Unknown argument: $arg" >&2; exit 1 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
TF_DIR="${ROOT_DIR}/terraform"

log() { echo "[teardown-db] $*"; }
tf()  { terraform -chdir="$TF_DIR" "$@"; }
tfo() { terraform -chdir="$TF_DIR" output -raw "$1"; }

# run_teardown_task <task_def_arn>
# Launch the teardown task (bootstrap task definition, command overridden to
# app.dbteardown) in the private subnets + ECS tasks SG, wait for it to STOP, and
# fail unless the container exited 0. CONFIRM_TEARDOWN=1 is injected as an env
# override so app.dbteardown's accidental-run backstop is satisfied. Mirrors
# deploy.sh's run_db_bootstrap (wait + exit-code + log-tail).
run_teardown_task() {
  local taskdef="$1" cluster subnets sg container loggroup overrides task_arn task_id exit_code
  cluster="$(tfo db_cluster_arn)"
  subnets="$(tfo db_subnet_ids)"
  sg="$(tfo db_security_group_id)"
  container="$(tfo db_container_name)"
  loggroup="$(tfo db_log_group_name)"

  overrides="$(cat <<JSON
{"containerOverrides":[{"name":"${container}","command":["uv","run","python","-m","app.dbteardown"],"environment":[{"name":"CONFIRM_TEARDOWN","value":"1"}]}]}
JSON
)"

  log "Running the DB teardown task (drop database + role)..."
  task_arn="$(aws ecs run-task \
    --region "$AWS_REGION" \
    --cluster "$cluster" \
    --task-definition "$taskdef" \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[${subnets}],securityGroups=[${sg}],assignPublicIp=DISABLED}" \
    --overrides "$overrides" \
    --query 'tasks[0].taskArn' --output text)"
  [ -n "$task_arn" ] && [ "$task_arn" != "None" ] || { echo "[teardown-db] ERROR: failed to start the teardown task." >&2; return 1; }
  log "  Started ${task_arn##*/}; waiting for it to stop (up to ~10m)..."

  # `wait tasks-stopped` returns non-zero on its own timeout; don't let set -e
  # abort here — fall through to the exit-code check, which reports accurately.
  aws ecs wait tasks-stopped --region "$AWS_REGION" --cluster "$cluster" --tasks "$task_arn" || true

  exit_code="$(aws ecs describe-tasks --region "$AWS_REGION" --cluster "$cluster" --tasks "$task_arn" \
    --query "tasks[0].containers[?name=='${container}'].exitCode|[0]" --output text)"
  if [ "$exit_code" != "0" ]; then
    echo "[teardown-db] ERROR: teardown task did not succeed (container exit code: ${exit_code}). Log tail:" >&2
    task_id="${task_arn##*/}"
    aws logs get-log-events --region "$AWS_REGION" \
      --log-group-name "$loggroup" --log-stream-name "ecs/${container}/${task_id}" \
      --limit 40 --query 'events[*].message' --output text >&2 2>/dev/null || \
      echo "[teardown-db]   (no logs available — check CloudWatch group ${loggroup})" >&2
    return 1
  fi
  log "  Teardown task completed successfully."
}

# ── Preflight ─────────────────────────────────────────────────────────────────
for bin in terraform aws; do
  command -v "$bin" >/dev/null || { echo "[teardown-db] ERROR: '$bin' not found on PATH." >&2; exit 1; }
done
[ -f "${TF_DIR}/backend.tf" ] || { echo "[teardown-db] ERROR: terraform/backend.tf missing — run scripts/bootstrap-state.sh first." >&2; exit 1; }
[ -f "${TF_DIR}/terraform.tfvars" ] || { echo "[teardown-db] ERROR: terraform/terraform.tfvars missing." >&2; exit 1; }

# ── Resolve the db module (skip cleanly for stateless services) ────────────────
if ! DB_TASKDEF="$(tf output -raw db_task_definition_arn 2>/dev/null)" || [ -z "$DB_TASKDEF" ] || [ "$DB_TASKDEF" = "None" ]; then
  log "No db module in this stack (create_database = false) — nothing to tear down."
  exit 0
fi

DB_NAME="$(tfo db_name)"
DB_USER="$(tfo db_user)"

# ── Confirm (typed), then run ─────────────────────────────────────────────────
echo
echo "  ⚠  About to PERMANENTLY DROP from the shared RDS (region ${AWS_REGION}):"
echo "       database : ${DB_NAME}"
echo "       role     : ${DB_USER}"
echo "     This is IRREVERSIBLE and destroys all data in that database."
echo

if [ -z "$ASSUME_YES" ]; then
  printf "  Type the database name (%s) to confirm: " "$DB_NAME"
  read -r reply
  [ "$reply" = "$DB_NAME" ] || { echo "[teardown-db] Aborted — input did not match." >&2; exit 1; }
fi

run_teardown_task "$DB_TASKDEF" || { echo "[teardown-db] FAILED — teardown task did not succeed." >&2; exit 1; }

log "Database + role dropped. Next: terraform -chdir=terraform destroy (removes the secret, bootstrap role, log group, and task definition)."
