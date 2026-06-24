#!/usr/bin/env bash
# fetch-cognito-config.sh — Fetch the shared platform's Cognito config from SSM
# Parameter Store and write it into the local .env file.
#
# The Cognito user pool + Hosted UI domain are owned by the shared platform (the
# `infrastructure` repo), so they come from the platform namespace:
#
#   Reads from: /<environment>/platform/cognito-user-pool-id
#               /<environment>/platform/cognito-localdev-client-id
#               /<environment>/platform/cognito-domain
#   Writes to:  .env in the repo root (or the path given by --env-file)
#
# Use this to run a local session against REAL Cognito (LOCAL_DEV=false). With
# LOCAL_DEV=true auth is bypassed and these values are not needed.
#
# NOTE: deployed services create their OWN app client (in the `frontend`
# Terraform module), which registers that service's https://<service>.<domain>
# URLs — not localhost — so it can't drive a localhost login. This script instead
# uses the platform's dev-only local-dev client (registers localhost URLs), which
# only exists in the development environment. The API accepts the resulting token
# because validation is pool-level (it doesn't care which client minted it).
#
# Safe to run multiple times — updates existing .env keys in place and appends
# any that are missing. Never removes keys that are already in .env.
#
# Usage:
#   ./scripts/fetch-cognito-config.sh [--env <environment>] [options]
#
# Examples:
#   ./scripts/fetch-cognito-config.sh                       # development
#   ./scripts/fetch-cognito-config.sh --env staging
#   ./scripts/fetch-cognito-config.sh --env production --dry-run
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Detect sed flavour (BSD/macOS vs GNU/Linux)
if sed --version 2>/dev/null | grep -q 'GNU sed'; then
  SED_I=(-i)
else
  SED_I=(-i '')
fi

usage() {
  cat >&2 <<EOF
Usage: $(basename "$0") [--env <environment>] [options]

  --env           Platform environment: development | staging | production
                  (default: development). Selects the /<environment>/platform
                  SSM namespace.
  --aws-region    AWS region for SSM API calls (default: eu-west-2)
  --env-file      Path to the .env file to update (default: <repo-root>/.env)
  --dry-run       Print resolved values without modifying .env
EOF
  exit 1
}

# ── Parse arguments ───────────────────────────────────────────────────────────
ENV="development"
AWS_REGION="eu-west-2"
ENV_FILE="$ROOT/.env"
DRY_RUN=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env)        ENV="$2";        shift 2 ;;
    --aws-region) AWS_REGION="$2"; shift 2 ;;
    --env-file)   ENV_FILE="$2";   shift 2 ;;
    --dry-run)    DRY_RUN=true;    shift   ;;
    --help|-h)    usage ;;
    *)            echo "Unexpected argument: $1" >&2; usage ;;
  esac
done

PREFIX="/${ENV}/platform"

echo "Fetching Cognito config from SSM Parameter Store"
echo "  Path prefix: $PREFIX"
echo "  AWS region:  $AWS_REGION"
echo "  Target file: $ENV_FILE"
echo ""

# ── Fetch the three platform Cognito parameters in one API call ──────────────
raw_json=$(aws ssm get-parameters \
  --region "$AWS_REGION" \
  --names \
    "${PREFIX}/cognito-user-pool-id" \
    "${PREFIX}/cognito-localdev-client-id" \
    "${PREFIX}/cognito-domain" \
  --query "Parameters[*].{Name:Name,Value:Value}" \
  --output json)

# ── Extract each value from JSON using jq ────────────────────────────────────
get_param() {
  local key="$1"
  echo "$raw_json" | jq -r --arg key "$key" '.[] | select(.Name | endswith("/" + $key)) | .Value'
}

USER_POOL_ID="$(get_param cognito-user-pool-id)"
CLIENT_ID="$(get_param cognito-localdev-client-id)"
DOMAIN="$(get_param cognito-domain)"

# Fail clearly if the platform namespace is missing any of them.
missing=()
[[ -z "$USER_POOL_ID" ]] && missing+=("${PREFIX}/cognito-user-pool-id")
[[ -z "$CLIENT_ID" ]]    && missing+=("${PREFIX}/cognito-localdev-client-id")
[[ -z "$DOMAIN" ]]       && missing+=("${PREFIX}/cognito-domain")
if [[ ${#missing[@]} -gt 0 ]]; then
  echo "Error: missing SSM parameter(s):" >&2
  for m in "${missing[@]}"; do echo "  $m" >&2; done
  echo "Is the '${ENV}' platform deployed, and are you authenticated to the right account?" >&2
  if [[ "$ENV" != "development" ]]; then
    echo "Note: cognito-localdev-client-id is created in the DEVELOPMENT environment only" >&2
    echo "      (local-dev login is a dev-only convenience). Try --env development." >&2
  fi
  exit 1
fi

# The user pool ID is "<region>_<id>"; the prefix is the pool's region.
COGNITO_REGION="${USER_POOL_ID%%_*}"
[[ -z "$COGNITO_REGION" || "$COGNITO_REGION" == "$USER_POOL_ID" ]] && COGNITO_REGION="$AWS_REGION"

# ── Report and optionally update .env ─────────────────────────────────────────
# Helper: set or append a KEY=VALUE pair in the .env file.
set_env_key() {
  local key="$1"
  local value="$2"

  if $DRY_RUN; then
    echo "  [dry-run] $key=$value"
    return
  fi

  if [[ ! -f "$ENV_FILE" ]]; then
    touch "$ENV_FILE"
  fi

  if grep -qE "^${key}=" "$ENV_FILE" 2>/dev/null; then
    # Key exists — update it in place
    sed "${SED_I[@]}" "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
    echo "  updated  $key"
  else
    # Key absent — append it
    echo "${key}=${value}" >> "$ENV_FILE"
    echo "  added    $key"
  fi
}

echo "Values resolved from SSM:"
# API side: validates tokens at the POOL level (no app client id), and reads
# COGNITO_DOMAIN to enrich claims with the caller's email via the userInfo
# endpoint (/whoami, require_user).
set_env_key "COGNITO_USER_POOL_ID"      "$USER_POOL_ID"
set_env_key "COGNITO_REGION"            "$COGNITO_REGION"
set_env_key "COGNITO_DOMAIN"            "$DOMAIN"
# Frontend side: logs in against the dev-only local-dev client and needs its id,
# the Hosted UI domain, and the localhost redirect URI registered on that client.
set_env_key "VITE_COGNITO_USER_POOL_ID" "$USER_POOL_ID"
set_env_key "VITE_COGNITO_CLIENT_ID"    "$CLIENT_ID"
set_env_key "VITE_COGNITO_DOMAIN"       "$DOMAIN"
set_env_key "VITE_COGNITO_REDIRECT_URI" "http://localhost:5173/callback"

echo ""
if $DRY_RUN; then
  echo "Dry run complete — .env was not modified."
else
  echo "Done. $ENV_FILE updated with Cognito config."
  echo "To exercise the real auth flow locally, set LOCAL_DEV=false and restart:"
  echo "  docker compose up"
fi
