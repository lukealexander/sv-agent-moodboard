#!/usr/bin/env bash
# cognito-test-token.sh — Mint a real Cognito ACCESS TOKEN headlessly (no browser)
# so you can exercise the API's real, pool-level token validation from the shell.
#
# It looks up the platform's dev-only local-dev app client id from SSM:
#
#   Reads from: /<environment>/platform/cognito-localdev-client-id
#
# then runs the USER_PASSWORD_AUTH flow against it and prints the resulting
# access token to stdout (nothing else goes to stdout, so it pipes cleanly).
#
#   TOKEN=$(./scripts/cognito-test-token.sh -u dev-test@example.com -p 'hunter2')
#   curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/whoami
#
# REQUIRES A NATIVE TEST USER. USER_PASSWORD_AUTH only works for a user with a
# Cognito-native password — Entra-federated users have none. Create one ONCE
# (development pool only; keep it OUT of Terraform so no standing credential
# lives in state):
#
#   POOL=$(aws ssm get-parameter --region eu-west-2 \
#     --name /development/platform/cognito-user-pool-id --query Parameter.Value --output text)
#   aws cognito-idp admin-create-user --user-pool-id "$POOL" \
#     --username dev-test@example.com --message-action SUPPRESS
#   aws cognito-idp admin-set-user-password --user-pool-id "$POOL" \
#     --username dev-test@example.com --password 'hunter2' --permanent
#
# The local-dev client (and this param) exist in the DEVELOPMENT environment only.
#
# Usage:
#   ./scripts/cognito-test-token.sh -u <username> -p <password> [options]
#
# Credentials may also come from the COGNITO_TEST_USERNAME / COGNITO_TEST_PASSWORD
# environment variables (flags win). Prefer the env vars or an interactive prompt
# over -p to keep the password out of your shell history.
set -euo pipefail

usage() {
  cat >&2 <<EOF
Usage: $(basename "$0") -u <username> -p <password> [options]

  -u, --username    Native Cognito username (email). Or set COGNITO_TEST_USERNAME.
  -p, --password    That user's password. Or set COGNITO_TEST_PASSWORD.
      --env         Platform environment: development (default). The local-dev
                    client only exists in development.
      --aws-region  AWS region for SSM + Cognito API calls (default: eu-west-2)
      --full        Print the full initiate-auth JSON (id/access/refresh) instead
                    of just the access token.
EOF
  exit 1
}

# ── Parse arguments ───────────────────────────────────────────────────────────
ENV="development"
AWS_REGION="eu-west-2"
USERNAME="${COGNITO_TEST_USERNAME:-}"
PASSWORD="${COGNITO_TEST_PASSWORD:-}"
FULL=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    -u|--username) USERNAME="$2";   shift 2 ;;
    -p|--password) PASSWORD="$2";   shift 2 ;;
    --env)         ENV="$2";        shift 2 ;;
    --aws-region)  AWS_REGION="$2"; shift 2 ;;
    --full)        FULL=true;       shift   ;;
    --help|-h)     usage ;;
    *)             echo "Unexpected argument: $1" >&2; usage ;;
  esac
done

[[ -z "$USERNAME" ]] && { echo "Error: username is required (-u / COGNITO_TEST_USERNAME)." >&2; usage; }
[[ -z "$PASSWORD" ]] && { echo "Error: password is required (-p / COGNITO_TEST_PASSWORD)." >&2; usage; }

PREFIX="/${ENV}/platform"

# ── Resolve the local-dev app client id from SSM ─────────────────────────────
# Progress goes to stderr so stdout carries only the token.
echo "Resolving local-dev client id from ${PREFIX}/cognito-localdev-client-id ..." >&2
CLIENT_ID="$(aws ssm get-parameter \
  --region "$AWS_REGION" \
  --name "${PREFIX}/cognito-localdev-client-id" \
  --query "Parameter.Value" \
  --output text 2>/dev/null || true)"

if [[ -z "$CLIENT_ID" || "$CLIENT_ID" == "None" ]]; then
  echo "Error: ${PREFIX}/cognito-localdev-client-id not found." >&2
  if [[ "$ENV" != "development" ]]; then
    echo "       The local-dev client exists in the DEVELOPMENT environment only." >&2
  fi
  echo "       Is the '${ENV}' platform deployed, and are you authenticated?" >&2
  exit 1
fi

# ── Run USER_PASSWORD_AUTH and emit the access token ─────────────────────────
auth_json="$(aws cognito-idp initiate-auth \
  --region "$AWS_REGION" \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id "$CLIENT_ID" \
  --auth-parameters "USERNAME=${USERNAME},PASSWORD=${PASSWORD}" \
  --output json)"

if $FULL; then
  echo "$auth_json" | jq '.AuthenticationResult'
  exit 0
fi

ACCESS_TOKEN="$(echo "$auth_json" | jq -r '.AuthenticationResult.AccessToken // empty')"
if [[ -z "$ACCESS_TOKEN" ]]; then
  # A challenge (e.g. NEW_PASSWORD_REQUIRED) means no token was issued — surface it.
  echo "Error: no access token in the auth result. Full response:" >&2
  echo "$auth_json" >&2
  exit 1
fi

echo "$ACCESS_TOKEN"
