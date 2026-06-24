#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Detect sed flavour: BSD sed (macOS) requires -i '' whereas GNU sed (Linux) uses -i
if sed --version 2>/dev/null | grep -q 'GNU sed'; then
  SED_I=(-i)
else
  SED_I=(-i '')
fi

usage() {
  cat >&2 <<EOF
Usage: $(basename "$0") <service-name> [--title <title>] [--description <description>]

  service-name   Slug for service references — lowercase letters, digits, hyphens (e.g. my-app)
  --title        Display name for the README heading (default: derived from service-name)
  --description  One-line project description for the README

Examples:
  ./scripts/init-project.sh my-tool
  ./scripts/init-project.sh my-tool --title "My Tool" --description "A tool for doing things"
EOF
  exit 1
}

# --- Parse arguments ---
SERVICE_NAME=""
TITLE=""
DESCRIPTION=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --title)       TITLE="$2";       shift 2 ;;
    --description) DESCRIPTION="$2"; shift 2 ;;
    --help|-h)     usage ;;
    -*)            echo "Unknown option: $1" >&2; usage ;;
    *)
      if [[ -z "$SERVICE_NAME" ]]; then
        SERVICE_NAME="$1"; shift
      else
        echo "Unexpected argument: $1" >&2; usage
      fi
      ;;
  esac
done

if [[ -z "$SERVICE_NAME" ]]; then
  echo "Error: service-name is required." >&2
  usage
fi

if ! [[ "$SERVICE_NAME" =~ ^[a-z0-9]([a-z0-9-]*[a-z0-9])?$ ]]; then
  echo "Error: service-name must be lowercase letters, digits, and hyphens (e.g. my-app)" >&2
  exit 1
fi

# Derive display title from service name if not provided (my-app -> My App)
if [[ -z "$TITLE" ]]; then
  TITLE="$(echo "$SERVICE_NAME" | sed 's/-/ /g' | awk '{for(i=1;i<=NF;i++) $i=toupper(substr($i,1,1)) substr($i,2)} 1')"
fi

echo "Initialising project: $SERVICE_NAME"
echo "  Title:       $TITLE"
echo "  Description: ${DESCRIPTION:-'(not set — placeholder left in README)'}"
echo ""

# --- 1. Replace README ---
echo "-> Replacing README.md"
cp "$ROOT/templates/new-project-README.md" "$ROOT/README.md"
sed "${SED_I[@]}" "s|\[PROJECT NAME\]|$TITLE|g" "$ROOT/README.md"
if [[ -n "$DESCRIPTION" ]]; then
  sed "${SED_I[@]}" "s|\[Description of project\]|$DESCRIPTION|g" "$ROOT/README.md"
fi

# --- 2. Replace TODO ---
echo "-> Replacing TODO.md"
cp "$ROOT/templates/new-project-TODO.md" "$ROOT/TODO.md"

# --- 3. Rename sv-skeleton references in source files ---
echo "-> Renaming 'sv-skeleton' -> '$SERVICE_NAME' in source files"
for f in \
  "$ROOT/apps/api/app/main.py" \
  "$ROOT/apps/frontend/src/pages/Home.tsx" \
  "$ROOT/apps/frontend/e2e/dashboard.spec.ts" \
  "$ROOT/docs/architecture.md"
do
  [[ -f "$f" ]] && sed "${SED_I[@]}" "s|sv-skeleton|$SERVICE_NAME|g" "$f"
done

# --- 4. Create terraform/terraform.tfvars from example (if it doesn't exist) ---
TFVARS="$ROOT/terraform/terraform.tfvars"
TFVARS_EXAMPLE="$ROOT/terraform/terraform.tfvars.example"
if [[ -f "$TFVARS_EXAMPLE" && ! -f "$TFVARS" ]]; then
  echo "-> Creating terraform/terraform.tfvars (service_name set to '$SERVICE_NAME')"
  cp "$TFVARS_EXAMPLE" "$TFVARS"
  sed "${SED_I[@]}" "s|^service_name[[:space:]]*=.*|service_name          = \"$SERVICE_NAME\"|" "$TFVARS"
elif [[ -f "$TFVARS" ]]; then
  echo "-> terraform/terraform.tfvars already exists — skipping (update service_name manually if needed)"
fi

# --- 5. Remove SPEC.md (skeleton spec, not needed in new projects) ---
if [[ -f "$ROOT/SPEC.md" ]]; then
  echo "-> Removing SPEC.md"
  rm "$ROOT/SPEC.md"
fi

# --- 6. Remove templates/ (consumed) ---
if [[ -d "$ROOT/templates" ]]; then
  echo "-> Removing templates/"
  rm -rf "$ROOT/templates"
fi

echo ""
echo "Done. A few things still need manual attention:"
echo "  1. Initialise the deployment modules submodule:"
echo "       git submodule update --init terraform/modules"
echo "  2. Set terraform/terraform.tfvars github_repo to this repo (org/repo),"
echo "     and export TF_VAR_github_access_token (GitHub PAT for Amplify)."
echo "  3. Update .github/copilot-instructions.md for your project"
if [[ -z "$DESCRIPTION" ]]; then
  echo "  4. Replace '[Description of project]' in README.md"
fi
echo ""
echo "To start locally:"
echo "  cp .env.example .env"
echo "  # edit .env (set CORS_ALLOWED_ORIGINS etc.)"
echo "  docker compose up"
