#!/usr/bin/env bash
# Usage: [IMAGE_TAG=v1.2.3] [AWS_REGION=eu-west-2] [FORCE_DB_BOOTSTRAP=1] [--skip-frontend] ./scripts/deploy.sh
#
# service_name is read from terraform/terraform.tfvars (Terraform auto-loads it);
# there is no SERVICE_NAME env var to set.
#
# Deploys this service onto the shared Supervenient AI platform:
#   1. ECR bootstrap — targeted apply creates the API's ECR repo (first run),
#      so there is somewhere to push before the ECS service tries to pull.
#   2. Build the ARM64 API image and push it to ECR.
#   3. Full `terraform apply` with the new image — registers a new task
#      definition revision and reconciles the ECS service, ALB target group +
#      listener rule, and the Amplify app/branch.
#   4. Roll out the new API task definition EXPLICITLY (the service ignores
#      task_definition changes, so apply alone won't repoint it), then WAIT for
#      the rollout to settle — failing if the circuit breaker rolls it back.
#   5. Trigger an Amplify frontend release and WAIT for the build to finish,
#      failing (and printing the build log) if it does not succeed.
#
# The frontend is hosted on AWS Amplify and built ON GIT PUSH — there is no
# frontend Docker build, S3 sync, or CloudFront invalidation here anymore.
#
# Prerequisites:
#   - AWS credentials configured (env vars / SSO / ~/.aws)
#   - docker (with linux/arm64 build support), aws-cli, terraform, curl on PATH
#   - scripts/bootstrap-state.sh already run once (terraform/backend.tf exists)
#   - terraform/terraform.tfvars exists (copied from terraform.tfvars.example,
#     with service_name + github_repo filled in)
#   - Amplify repo access set up: usually the Amplify GitHub App (nothing to
#     export). Only export TF_VAR_github_access_token (a GitHub PAT) if you are
#     NOT using the App and the app's access_token is managed by Terraform.

set -euo pipefail

IMAGE_TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD 2>/dev/null || echo "latest")}"
AWS_REGION="${AWS_REGION:-eu-west-2}"
# Force the one-shot DB bootstrap task to run even when the DATABASE_URL secret is
# already populated (e.g. to re-provision after the role/db was dropped). Normally
# left unset: provisioning is one-time and migrations run on API startup.
FORCE_DB_BOOTSTRAP="${FORCE_DB_BOOTSTRAP:-}"
TRIGGER_FRONTEND=true

for arg in "$@"; do
  case "$arg" in
    --skip-frontend) TRIGGER_FRONTEND=false ;;
    *) echo "Unknown argument: $arg" >&2; exit 1 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
TF_DIR="${ROOT_DIR}/terraform"

log() { echo "[deploy] $*"; }
tf()  { terraform -chdir="$TF_DIR" "$@"; }
tfo() { terraform -chdir="$TF_DIR" output -raw "$1"; }

# ensure_arm64_emulation
# The API image is built for linux/arm64 (Graviton). On a non-arm64 host that
# requires QEMU binfmt emulation, without which the build dies at the first RUN
# with "exec format error". The registration is NOT persistent on some setups
# (e.g. WSL2 drops it on shutdown), so register it on demand here — idempotent
# and a no-op when the handler is already enabled or the host is natively arm64.
ensure_arm64_emulation() {
  case "$(uname -m)" in
    aarch64|arm64) return 0 ;;  # native arm64 host — no emulation needed
  esac
  if grep -qx enabled /proc/sys/fs/binfmt_misc/qemu-aarch64 2>/dev/null; then
    return 0
  fi
  log "Registering QEMU arm64 emulation (binfmt handler missing)..."
  docker run --privileged --rm tonistiigi/binfmt --install arm64 >/dev/null
}

# wait_for_ecs_rollout <cluster> <service> <task_def_arn>
# Block until the service's PRIMARY deployment reaches a terminal state. Succeeds
# only if it COMPLETED on the task def we just shipped; fails on a circuit-breaker
# FAILED state, on a rollback to a different revision, or on timeout — so a
# rolled-back deploy is reported as failure instead of looking like success.
wait_for_ecs_rollout() {
  local cluster="$1" service="$2" want="$3"
  local deadline=$(( SECONDS + 900 )) state taskdef
  log "Waiting for the ECS rollout to settle (up to 15m)..."
  while :; do
    read -r state taskdef <<<"$(aws ecs describe-services --region "$AWS_REGION" \
      --cluster "$cluster" --services "$service" \
      --query "services[0].deployments[?status=='PRIMARY']|[0].[rolloutState,taskDefinition]" \
      --output text)"
    case "$state" in
      COMPLETED)
        [ "$taskdef" = "$want" ] && { log "ECS rollout completed on the new task definition."; return 0; }
        echo "[deploy] ERROR: ECS rolled back — service is running ${taskdef}, not the revision we deployed. A failed container health check likely tripped the circuit breaker." >&2
        return 1 ;;
      FAILED)
        echo "[deploy] ERROR: ECS deployment FAILED (circuit breaker tripped). Recent service events:" >&2
        aws ecs describe-services --region "$AWS_REGION" --cluster "$cluster" --services "$service" \
          --query 'services[0].events[0:5].message' --output text >&2
        return 1 ;;
    esac
    (( SECONDS > deadline )) && { echo "[deploy] ERROR: ECS rollout did not settle within 15m (last state: ${state:-unknown})." >&2; return 1; }
    sleep 15
  done
}

# wait_for_amplify_job <app_id> <branch> <job_id>
# Block until the Amplify build finishes; fails (printing the build log tail)
# unless it SUCCEEDs.
wait_for_amplify_job() {
  local app="$1" branch="$2" job="$3"
  local deadline=$(( SECONDS + 1200 )) status url
  log "Waiting for Amplify job ${job} to finish (up to 20m)..."
  while :; do
    status="$(aws amplify get-job --region "$AWS_REGION" --app-id "$app" \
      --branch-name "$branch" --job-id "$job" --query 'job.summary.status' --output text)"
    log "  Amplify job ${job}: ${status}"
    case "$status" in
      SUCCEED) log "Amplify build succeeded."; return 0 ;;
      FAILED|CANCELLED)
        echo "[deploy] ERROR: Amplify job ${job} ${status}. Build log tail:" >&2
        url="$(aws amplify get-job --region "$AWS_REGION" --app-id "$app" --branch-name "$branch" \
          --job-id "$job" --query "job.steps[?stepName=='BUILD'].logUrl|[0]" --output text)"
        [ -n "$url" ] && [ "$url" != "None" ] && curl -sS --max-time 20 "$url" | tail -40 >&2
        return 1 ;;
    esac
    (( SECONDS > deadline )) && { echo "[deploy] ERROR: Amplify job ${job} did not finish within 20m (last status: ${status:-unknown})." >&2; return 1; }
    sleep 15
  done
}

# db_secret_populated <secret_arn>
# True (exit 0) when the DATABASE_URL secret already holds a value — i.e. the
# bootstrap task has provisioned this service's role+database at least once. The
# secret resource is created empty by Terraform, so get-secret-value fails (no
# AWSCURRENT version) until the task writes it; we treat that failure as "not yet
# provisioned". Used to skip the slow one-shot task on routine deploys.
db_secret_populated() {
  local val
  val="$(aws secretsmanager get-secret-value --region "$AWS_REGION" \
    --secret-id "$1" --query 'SecretString' --output text 2>/dev/null)" || return 1
  [ -n "$val" ] && [ "$val" != "None" ]
}

# run_db_bootstrap
# Launch the db module's one-shot Fargate task (aws ecs run-task) in the private
# subnets + ECS tasks SG (the only ingress RDS allows), wait for it to STOP, and
# fail unless its container exited 0. The task creates this service's role +
# database on the shared RDS, writes the DATABASE_URL secret, and runs
# `alembic upgrade head`. All steps are idempotent, but the cold Fargate start is
# slow (~minutes), so deploy.sh runs it ONLY for first-time provisioning (see
# below) — routine migrations are applied on API startup by docker-entrypoint.sh.
# Reads db_* outputs published by the db module (see terraform/outputs.tf).
run_db_bootstrap() {
  local cluster subnets sg container loggroup taskdef task_arn task_id exit_code
  taskdef="$1"
  cluster="$(tfo db_cluster_arn)"
  subnets="$(tfo db_subnet_ids)"
  sg="$(tfo db_security_group_id)"
  container="$(tfo db_container_name)"
  loggroup="$(tfo db_log_group_name)"

  log "Running the DB bootstrap task (provision role+database, write secret, migrate)..."
  task_arn="$(aws ecs run-task \
    --region "$AWS_REGION" \
    --cluster "$cluster" \
    --task-definition "$taskdef" \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[${subnets}],securityGroups=[${sg}],assignPublicIp=DISABLED}" \
    --query 'tasks[0].taskArn' --output text)"
  [ -n "$task_arn" ] && [ "$task_arn" != "None" ] || { echo "[deploy] ERROR: failed to start the DB bootstrap task." >&2; return 1; }
  log "  Started ${task_arn##*/}; waiting for it to stop (up to ~10m)..."

  # `wait tasks-stopped` returns non-zero on its own timeout; don't let set -e
  # abort here — fall through to the exit-code check, which reports accurately.
  aws ecs wait tasks-stopped --region "$AWS_REGION" --cluster "$cluster" --tasks "$task_arn" || true

  exit_code="$(aws ecs describe-tasks --region "$AWS_REGION" --cluster "$cluster" --tasks "$task_arn" \
    --query "tasks[0].containers[?name=='${container}'].exitCode|[0]" --output text)"
  if [ "$exit_code" != "0" ]; then
    echo "[deploy] ERROR: DB bootstrap task did not succeed (container exit code: ${exit_code}). Log tail:" >&2
    task_id="${task_arn##*/}"
    aws logs get-log-events --region "$AWS_REGION" \
      --log-group-name "$loggroup" --log-stream-name "ecs/${container}/${task_id}" \
      --limit 40 --query 'events[*].message' --output text >&2 2>/dev/null || \
      echo "[deploy]   (no logs available — check CloudWatch group ${loggroup})" >&2
    return 1
  fi
  log "  DB bootstrap task completed successfully."
}

# Set false by any deployment that fails its wait; checked once at the end so a
# broken backend doesn't skip the frontend deploy (and vice versa).
DEPLOY_OK=true

# ── Preflight: machine-local prerequisites (fail early, not mid-apply) ─────────
# Each check maps to a failure that otherwise only surfaces deep inside a
# terraform apply on a fresh checkout (empty local state, unset Amplify token).
for bin in terraform docker aws curl; do
  command -v "$bin" >/dev/null || { echo "[deploy] ERROR: '$bin' not found on PATH." >&2; exit 1; }
done
[ -f "${TF_DIR}/backend.tf" ] || { echo "[deploy] ERROR: terraform/backend.tf missing — run scripts/bootstrap-state.sh first, or Terraform uses empty LOCAL state and tries to recreate everything." >&2; exit 1; }
[ -f "${TF_DIR}/terraform.tfvars" ] || { echo "[deploy] ERROR: terraform/terraform.tfvars missing — cp terraform/terraform.tfvars.example terraform/terraform.tfvars and set service_name + github_repo." >&2; exit 1; }

# ── 1. ECR bootstrap (idempotent) ─────────────────────────────────────────────
# The api module CREATES the ECR repo, but the image must exist before the ECS
# service can pull it. Apply just the repo first to break the chicken-and-egg.
log "Ensuring ECR repository exists (targeted apply)..."
tf apply -input=false -auto-approve \
  -target=module.api.aws_ecr_repository.this

ECR_REPO_URL="$(tfo ecr_repository_url)"
IMAGE_URI="${ECR_REPO_URL}:${IMAGE_TAG}"
ECR_REGISTRY="${ECR_REPO_URL%%/*}"

# ── 2. Build + push the API image (ARM64 — MUST match the module default) ──────
log "Authenticating Docker with ECR (${ECR_REGISTRY})..."
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$ECR_REGISTRY"

ensure_arm64_emulation

log "Building API image ${IMAGE_URI} (linux/arm64)..."
docker build \
  --target prod \
  --platform linux/arm64 \
  -t "$IMAGE_URI" \
  "${ROOT_DIR}/apps/api"

log "Pushing ${IMAGE_URI}..."
docker push "$IMAGE_URI"

# ── 3. Full apply with the new image ──────────────────────────────────────────
log "Applying full stack with container_image=${IMAGE_URI}..."
tf apply -input=false -auto-approve \
  -var "container_image=${IMAGE_URI}"

# ── 3b. Provision the database (one-shot bootstrap task — first deploy only) ───
# The bootstrap task creates this service's role+database and writes the
# DATABASE_URL secret. It's needed exactly ONCE per service; routine schema
# migrations are applied on API startup (apps/api/docker-entrypoint.sh runs
# `alembic upgrade head` before uvicorn), so we no longer pay the slow Fargate
# cold start on every deploy.
#
# Run the task only when the DATABASE_URL secret is still empty (never
# provisioned) — or when FORCE_DB_BOOTSTRAP is set, to re-provision on demand.
# Stateless services have no db_* outputs, so this is skipped automatically. A
# bootstrap failure is fatal: don't roll the API onto an unprovisioned database.
if DB_TASKDEF="$(tf output -raw db_task_definition_arn 2>/dev/null)" && [ -n "$DB_TASKDEF" ] && [ "$DB_TASKDEF" != "None" ]; then
  DB_SECRET_ARN="$(tf output -raw db_url_secret_arn 2>/dev/null || true)"
  if [ -z "$FORCE_DB_BOOTSTRAP" ] && [ -n "$DB_SECRET_ARN" ] && [ "$DB_SECRET_ARN" != "None" ] && db_secret_populated "$DB_SECRET_ARN"; then
    log "Database already provisioned (DATABASE_URL secret is populated) — skipping the one-shot bootstrap task."
    log "  Migrations will be applied on API startup. Set FORCE_DB_BOOTSTRAP=1 to re-run the task."
  else
    [ -n "$FORCE_DB_BOOTSTRAP" ] && log "FORCE_DB_BOOTSTRAP set — running the bootstrap task regardless of secret state."
    run_db_bootstrap "$DB_TASKDEF" || { echo "[deploy] FAILED — database bootstrap did not succeed; not rolling out the API." >&2; exit 1; }
  fi
else
  log "No db module in this stack — skipping database bootstrap (stateless service)."
fi

# ── 4. Roll out the new API task definition explicitly ────────────────────────
# The service uses ignore_changes = [task_definition], so `apply` won't repoint
# it, and a bare --force-new-deployment would redeploy the OLD revision. Point
# the service at the revision the apply just registered.
log "Rolling out the new API task definition..."
ECS_CLUSTER="$(tfo cluster_arn)"
ECS_SERVICE="$(tfo ecs_service_name)"
ECS_TASKDEF="$(tfo task_definition_arn)"
aws ecs update-service \
  --region "$AWS_REGION" \
  --cluster "$ECS_CLUSTER" \
  --service "$ECS_SERVICE" \
  --task-definition "$ECS_TASKDEF" \
  --force-new-deployment \
  --query 'service.{service:serviceName,taskDefinition:taskDefinition}' \
  --output table

if ! wait_for_ecs_rollout "$ECS_CLUSTER" "$ECS_SERVICE" "$ECS_TASKDEF"; then
  DEPLOY_OK=false
fi

# ── 5. Frontend: Amplify builds on git push; optionally trigger a release ──────
if $TRIGGER_FRONTEND; then
  AMPLIFY_APP_ID="$(tfo amplify_app_id)"
  AMPLIFY_BRANCH="$(tfo amplify_branch_name)"
  log "Triggering Amplify release (app ${AMPLIFY_APP_ID}, branch ${AMPLIFY_BRANCH})..."
  AMPLIFY_JOB_ID="$(aws amplify start-job \
    --region "$AWS_REGION" \
    --app-id "$AMPLIFY_APP_ID" \
    --branch-name "$AMPLIFY_BRANCH" \
    --job-type RELEASE \
    --query 'jobSummary.jobId' --output text)"
  if ! wait_for_amplify_job "$AMPLIFY_APP_ID" "$AMPLIFY_BRANCH" "$AMPLIFY_JOB_ID"; then
    DEPLOY_OK=false
  fi
else
  log "Skipping Amplify release trigger (--skip-frontend). Amplify still auto-builds on git push."
fi

if ! $DEPLOY_OK; then
  echo "[deploy] FAILED — one or more deployments did not succeed (see errors above)." >&2
  exit 1
fi

log "Deploy complete."
log "  API:      $(tfo api_url)"
log "  Frontend: $(tfo frontend_url)"
