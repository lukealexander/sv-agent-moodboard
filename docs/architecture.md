# Architecture

This project is built on the Supervenient skeleton and as such has a number of architectural assumptions baked in.  

This document describes how the api, frontend, terraform cconfig and default docker arrangement are set up. It should
be updated regularly, and should always match information in the live project.

## Repository layout

```
agent-moodboard/
├── apps/
│   ├── api/                     FastAPI backend (Python 3.12, async SQLAlchemy)
│   │   ├── app/
│   │   │   ├── main.py          App factory; registers routers + CORS
│   │   │   ├── config.py        Pydantic settings (env-driven)
│   │   │   ├── routers/         HTTP routes
│   │   │   │   ├── health.py    GET /health           (public)
│   │   │   │   ├── me.py        GET /whoami           (protected)
│   │   │   │   └── items.py     GET /items, /items/id (protected, example resource)
│   │   │   ├── dependencies/
│   │   │   │   └── auth.py      require_auth: Cognito JWT validation / local-dev bypass
│   │   │   ├── db/
│   │   │   │   ├── base.py      SQLAlchemy DeclarativeBase
│   │   │   │   └── session.py   Lazy async engine + get_db() dependency
│   │   │   └── models/          ORM models (re-exported in __init__ for Alembic)
│   │   ├── alembic/             Migration environment + versions/
│   │   ├── tests/               Pytest suite (see docs/testing.md)
│   │   ├── pyproject.toml       Deps + pytest/coverage config
│   │   └── Dockerfile           Multi-stage: dev (uvicorn --reload) / prod (workers)
│   └── frontend/                React 18 + Vite + TanStack Query + CSS Modules
│       ├── src/
│       │   ├── App.tsx          Router + providers
│       │   ├── auth/            Cognito PKCE flow + AuthContext
│       │   ├── api/client.ts    QueryClient + fetchWithAuth wrapper
│       │   ├── components/      ProtectedRoute, Modal
│       │   ├── pages/           Login, Callback, Home (status dashboard)
│       │   └── styles/          global.css + design tokens (CSS Modules only)
│       ├── e2e/                 Playwright end-to-end tests (see docs/testing.md)
│       ├── playwright.config.ts
│       └── Dockerfile           Multi-stage: dev (vite) / build / prod (nginx)
├── terraform/                   Thin root composing the shared `deployment` modules
│   ├── main.tf                  module "api" (Fargate) + module "frontend" (Amplify)
│   └── modules/                 git submodule → Supervenient-AI/deployment
├── scripts/
│   ├── bootstrap-state.sh       One-time: create S3/DynamoDB Terraform backend
│   └── deploy.sh                Build → push → sync → terraform apply
├── .devcontainer/               VS Code devcontainer (AWS CLI + Terraform + Node)
├── docker-compose.yml           Local dev: api + postgres + frontend
└── docs/                        You are here
```

## The three layers

| Layer | Tech | Local entry point | Deployed at |
|---|---|---|---|
| Frontend | React + Vite | `:5173` | `https://<service>.labs.supervenient.ai` (AWS Amplify, build-on-push) |
| API | FastAPI + uvicorn | `:8000` | `https://<service>.api.labs.supervenient.ai` (ECS Fargate behind the shared ALB) |
| Database | PostgreSQL (optional) | `:5432` | shared platform RDS (opt-in via a Secrets Manager `DATABASE_URL`) |

## Auth model

Auth is the load-bearing convention of this template. The frontend authenticates the
**user** via Cognito Hosted UI; the API independently validates the **token**.

```
Browser ──Cognito Hosted UI (PKCE)──▶ Cognito
   │  ◀── id/access/refresh tokens ──┘
   │
   └── GET /items  (Authorization: Bearer <access_token>) ──▶ API
                                                               │
                                          validates token vs Cognito JWKS
```

* **Per-service app client for login, pool-level validation for APIs.** This service
  creates its **own** Cognito app client (in the `frontend` module) inside the **shared**
  user pool, owning its own callback (`https://<service>.<domain_base>/callback`) and
  logout (`https://<service>.<domain_base>`) URLs — so onboarding a service needs no
  change to the platform repo. The frontend logs in against that client and sends the
  **access token** to APIs. The API validates tokens at the **pool level** (signature +
  `iss` = the pool issuer + `token_use == "access"`), derived from the pool id + region —
  it is **not** bound to one app client. So a token minted for any service's client in the
  pool is accepted, which is what makes **cross-service** and **api-to-api** calls work;
  set `COGNITO_ALLOWED_CLIENT_IDS` to restrict callers (defense in depth).
* **SSO is automatic.** Because the user pool and Hosted UI domain are shared, the Hosted
  UI session cookie (scoped to the pool, not the client) carries across services — after
  logging into one service, opening another authenticates silently, no second prompt.
* **Public vs protected is explicit.** There is no global auth middleware. A route is
  protected by depending on `require_auth` (see [backend.md](backend.md)); a public
  route simply omits it. `/health` is public; `/whoami` and `/items` are protected.
* **Local dev bypasses auth.** With `LOCAL_DEV=true` the API's `require_auth` returns a
  stub user and the frontend's `AuthProvider` boots already-authenticated, so you can
  develop without a Cognito round-trip. This is also what makes the test suites
  hermetic.
* **Local dev against real Cognito** (`LOCAL_DEV=false`) is also supported. The deployed
  per-service client only registers `https://<service>.<domain>` URLs, so the platform
  additionally publishes a **dev-only local-dev client** — the one client registering
  `http://localhost:5173` callback/logout URLs (`COGNITO` + `EntraID`), and existing in
  the **development** environment only. `scripts/fetch-cognito-config.sh` pulls its id
  into `.env`; `scripts/cognito-test-token.sh` mints a headless access token against it
  for a native test user. See the README "Cognito configuration" section.

See [backend.md](backend.md) and [frontend.md](frontend.md) for the full flow.

## Request flow (production)

1. User hits the frontend; `ProtectedRoute` redirects unauthenticated users to `/login`.
2. `/login` redirects to Cognito Hosted UI with a PKCE challenge.
3. Cognito redirects back to `/callback?code=…`; the frontend exchanges the code for
   tokens and stores the refresh token in `localStorage`.
4. API calls carry `Authorization: Bearer <access_token>`.
5. The API validates the token's signature (against Cognito's JWKS, cached in-process),
   issuer, expiry, and `token_use == "access"` — pool-scoped, not pinned to one app
   client.

## Deploy flow

`scripts/deploy.sh` is the single command-line entry point:

1. **ECR bootstrap** — targeted `terraform apply` creates the API's ECR repo.
2. Build the API image (`--target prod`, `--platform linux/arm64`) and push it to ECR.
3. Full `terraform apply -var container_image=<ecr-url>:<tag>` — registers a new task
   definition and reconciles the ECS service, ALB rule, and the Amplify app.
3b. **Database provisioning (managed DB only)** — on a service's *first* deploy the script
   runs the one-shot Fargate bootstrap task to create its Postgres role + database and
   populate the `DATABASE_URL` secret. Later deploys skip this slow task; the API applies
   `alembic upgrade head` on startup (`apps/api/docker-entrypoint.sh`). Force a re-run with
   `FORCE_DB_BOOTSTRAP=1`.
4. Roll out the new task definition explicitly with `aws ecs update-service
   --task-definition … --force-new-deployment` (the service ignores `task_definition`
   changes, so `apply` alone won't ship the new image).
5. The frontend is built by **Amplify on git push**; the script also triggers a release
   via `aws amplify start-job`.

See [infrastructure.md](infrastructure.md) for the Terraform topology, the shared-platform
contract (SSM), and the one-shared-ALB convention.
