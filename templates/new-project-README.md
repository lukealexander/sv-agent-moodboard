# [PROJECT NAME]

[Description of project]

## What docs?

This is just a brief overview.  But there's a lot more detail in the individual docs in /docs. Start with [architecture.md](docs/architecture.md) for the big picture, then drill into the layer
you're working on.

| Doc | What it covers |
|---|---|
| [architecture.md](docs/architecture.md) | Repo layout, how the pieces fit together, request & deploy flows |
| [backend.md](docs/backend.md) | FastAPI app structure, auth, config, database layer, endpoints |
| [frontend.md](docs/frontend.md) | React/Vite app structure, Cognito auth flow, the status dashboard |
| [testing.md](docs/testing.md) | The pytest (API) and Playwright (e2e) suites — how to run and extend them |
| [infrastructure.md](docs/infrastructure.md) | Terraform modules, the deploy/bootstrap scripts, AWS topology |
| [design/](docs/design/) | Supervenient brand & design-token reference |


## What's included

| Layer | Stack |
|---|---|
| Backend | FastAPI + Alembic (PostgreSQL, SQLAlchemy 2.0 async) |
| Frontend | React 18 + Vite + React Router + TanStack Query + CSS Modules |
| Auth | AWS Cognito Hosted UI (PKCE), JWT validation on API |
| Infrastructure | Terraform consuming the shared `deployment` modules — Fargate API behind the shared platform ALB, Amplify-hosted frontend; platform discovered via SSM |
| Local dev | Docker Compose v2, `LOCAL_DEV=true` bypasses auth |
| Dev container | VS Code devcontainer with AWS CLI + Terraform pre-installed |
| Tests | Pytest (API: health, auth, items, /whoami, migrations) + Playwright (frontend e2e) |

See [docs/](docs/) for full architecture, backend, frontend, testing, and infra docs.

Deployed services land at:
- **API:** `https://<service>.api.labs.supervenient.ai`
- **Frontend:** `https://<service>.labs.supervenient.ai`

---

## Getting started (local)

```bash
cp .env.example .env
docker compose up
```

- Frontend: http://localhost:5173
- API docs: http://localhost:8000/docs
- Postgres: localhost:5432

Auth is disabled locally (`LOCAL_DEV=true`). All protected endpoints accept any `Authorization: Bearer <token>` value.

When running locally, you will still need to set CORS variables which can be found in .env.example.  These should be set to e.g. CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173.

### Run migrations

```bash
docker compose exec api alembic upgrade head
```

### Run tests

```bash
# API (Pytest) — hermetic, no real Cognito needed
docker compose exec api uv run pytest

# Frontend end-to-end (Playwright) — from apps/frontend
npm install && npx playwright install chromium
npm run test:e2e
```

See [docs/testing.md](docs/testing.md) for what's covered and how to extend the suites.

---

## Cognito configuration

The Cognito **user pool** and **Hosted UI domain** are owned by the **shared platform** (published to SSM); this service creates its **own app client** in that pool at deploy time (in the `frontend` Terraform module). The API validates access tokens at the **pool level** (issuer + signature + `token_use`), so it accepts tokens from any client in the pool and needs no app-client id.

The platform config lives in SSM under the platform namespace for each environment:

```
/<env>/platform/cognito-user-pool-id
/<env>/platform/cognito-localdev-client-id   # dev-only local-dev client (registers localhost URLs) — development env only
/<env>/platform/cognito-domain
```

You only need these to run a local session against **real** Cognito (`LOCAL_DEV=false`); with `LOCAL_DEV=true` auth is bypassed and they aren't required. The deployed per-service client registers `https://<service>.<domain>` URLs, not `localhost`, so it can't drive a local login — the platform publishes a **dev-only local-dev client** (the only one registering `http://localhost:5173`) for that, in the **development environment only**.

### Fetch into .env

First, log in to AWS:

```bash
aws sso login
```

Then pull the platform's Cognito values into your `.env` (updates existing keys in place, appends missing ones):

```bash
./scripts/fetch-cognito-config.sh    # development (the only env with a local-dev client)
```

This writes the pool id + region + `COGNITO_DOMAIN` (API side) and `VITE_COGNITO_CLIENT_ID` + `VITE_COGNITO_DOMAIN` + `VITE_COGNITO_REDIRECT_URI=http://localhost:5173/callback` (frontend side). Add `--dry-run` to preview without modifying anything.

---

## Using the skeleton template to create this project

This section assumes that you are reading this as README.md in the root, and that you have already run the init-project.sh script.

1. (already done) ~~Click **Use this template** on GitHub and create a new repo.~~
2. (already done) ~~Clone your new repo, then run the init script to strip out skeleton content and rename references:~~
   ~~```bash~~
   ~~./scripts/init-project.sh <service-name> --title "My Project" --description "What it does"~~
   ~~```~~
   ~~This replaces `README.md` and `TODO.md`, renames `sv-skeleton` throughout the source, and creates `terraform/terraform.tfvars` with `service_name` pre-filled.~~
3. Initialise the deployment-modules submodule and fill in the remaining Terraform vars:
   ```bash
   git submodule update --init terraform/modules
   # init-project.sh already created terraform/terraform.tfvars with service_name pre-filled.
   # Edit it: set github_repo (org/repo) and, optionally, create_database = true for a managed Postgres DB.
   export TF_VAR_github_access_token=ghp_xxx   # GitHub PAT Amplify uses
   ```
4. Bootstrap Terraform state (once per project):
   ```bash
   SERVICE_NAME=myapp ./scripts/bootstrap-state.sh
   cd terraform && terraform init
   ```
5. Optionally, run Impeccable in Claude Code or GitHub Copilot to set up a design system for the repo:
  ``` /impeccable init ```  

---

## Deploying

```bash
IMAGE_TAG=v1.0.0 ./scripts/deploy.sh
```

This builds the ARM64 API image, pushes it to ECR, runs `terraform apply`, then rolls
out the new ECS task definition and triggers an Amplify build. The frontend itself is
built by **Amplify on git push** — there is no S3 sync or CloudFront step.

To skip the explicit Amplify build trigger (Amplify still auto-builds on push):
```bash
IMAGE_TAG=v1.0.0 ./scripts/deploy.sh --skip-frontend
```

---

## Teardown

If you want to destroy all infrastructure associated with this project, do the following:

1. Drop this service's database + role from the **shared RDS** (a no-op if you never created one) by running `./scripts/teardown-db.sh`. Do this **before** destroy — the database is created with raw SQL and is **not** in Terraform state, so `terraform destroy` alone would leave it orphaned.
2. Run `cd terraform && terraform destroy`.

See [docs/infrastructure.md](docs/infrastructure.md) for the full DB lifecycle.

---

## Project structure

```
apps/
  api/          FastAPI backend
  frontend/     React/Vite frontend
terraform/
  main.tf       module "api" + module "frontend" calls
  modules/      git submodule → Supervenient-AI/deployment (api + frontend modules)
scripts/
  bootstrap-state.sh   Create S3/DynamoDB Terraform state backend
  deploy.sh            Build → push → apply → roll out → trigger Amplify
.devcontainer/         VS Code dev container config
docker-compose.yml
```

---

## Adding a second backend service

1. Create `apps/<service-name>/` with its own `Dockerfile` and FastAPI app.
2. Add a second `module "api"` call in `terraform/main.tf` with a distinct `name` and a
   **unique** `alb_listener_rule_priority` (see the commented example there).
3. The new service will be available at `https://<service-name>.api.labs.supervenient.ai`.

---

## Auth flow

**Local dev:** `LOCAL_DEV=true` — the `require_auth` dependency returns a stub user without calling Cognito.

**Production:**
1. User visits the frontend → `ProtectedRoute` → redirects to `/login`
2. `/login` → redirects to Cognito Hosted UI with PKCE challenge
3. Cognito → redirects to `/callback?code=...`
4. Frontend exchanges code for tokens, stores refresh token in `localStorage`
5. API requests include `Authorization: Bearer <access_token>`
6. FastAPI validates the token against Cognito's JWKS endpoint

**Declaring a public endpoint:**

```python
# Protected by default — just use require_auth dependency:
@router.get("/items", dependencies=[Depends(require_auth)])

# Public — use a plain router without the auth dependency:
public_router = APIRouter()

@public_router.get("/health")
async def health(): ...
```
