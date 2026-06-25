# Backend (FastAPI)

The API lives in [apps/api](../apps/api). It is a FastAPI app targeting Python 3.12,
using async SQLAlchemy 2.0 for the (optional) database layer and Alembic for
migrations. Dependencies are managed with `uv` (`uv.lock` is authoritative).

## Application structure

```
app/
├── main.py            App instance; CORS + router registration
├── config.py          Settings (pydantic-settings, env-driven)
├── routers/
│   ├── health.py      Public liveness probe
│   ├── me.py          /whoami — the caller's identity
│   └── items.py       Example protected CRUD-ish resource
├── dependencies/
│   └── auth.py        require_auth dependency
├── db/
│   ├── base.py        DeclarativeBase
│   └── session.py     Lazy engine + get_db()
└── models/
    └── item.py        Example ORM model
```

### `main.py`

Builds the `FastAPI` instance and:

* Exposes `/docs` and `/redoc` **only** in local dev (`settings.local_dev`).
* Configures CORS from `settings.cors_origins` (see below). When the allow-list is
  the wildcard `*`, `allow_credentials` is automatically disabled — browsers reject
  `Access-Control-Allow-Origin: *` together with credentials, so the two can't be set
  at once.
* Registers the `health`, `me`, and `items` routers.

### `config.py`

`Settings` (pydantic-settings) reads from environment / `.env`. Key fields:

| Setting | Purpose |
|---|---|
| `local_dev` | `LOCAL_DEV=true` bypasses auth and enables docs |
| `cognito_user_pool_id`, `cognito_region` | Pool-level token validation (issuer + JWKS) |
| `cognito_domain` | Hosted UI domain (bare host); enables userInfo email enrichment (`/whoami`, `require_user`). Empty = no email |
| `cognito_allowed_client_ids` | Optional comma-separated app-client allow-list; empty = accept any client in the pool |
| `cors_allowed_origins` | Comma-separated allow-list; **required when `LOCAL_DEV=false`** |
| `database_url` | Optional; the DB engine is only created if set |
| `aws_secrets_manager_secret_name` | Name of the runtime secret (injected in ECS) |

`settings` is a module-level singleton imported elsewhere with
`from app.config import settings`. Because every module shares that one object, tests
flip behaviour by mutating its attributes (see [testing.md](testing.md)).

Derived properties / validation:

* `cors_origins` — parses `cors_allowed_origins` into a list, defaulting to `["*"]` when
  unset (local dev only).
* A `model_validator` **fails fast at startup** if `LOCAL_DEV=false` and
  `cors_allowed_origins` is empty — production must declare its allowed origins
  explicitly rather than silently falling back to `*`.
* `cognito_issuer` is `https://cognito-idp.<region>.amazonaws.com/<pool>` and
  `cognito_jwks_url` hangs `/.well-known/jwks.json` off it. Both are derived from
  `cognito_user_pool_id` + `cognito_region` — no app client id required.
* `cognito_allowed_client_id_list` parses the optional client allow-list.

## Authentication — `dependencies/auth.py`

`require_auth` is the single gate for protected routes.

```python
async def require_auth(credentials = Depends(HTTPBearer(auto_error=False))) -> dict:
    if settings.local_dev:
        return {"sub": "local-dev-user", "email": "dev@local"}   # bypass
    # else: validate the bearer token against Cognito's JWKS
```

Production validation is **pool-scoped**, not bound to a single app client — so a
token minted for any service's client in the shared pool is accepted (this is what
makes cross-service and api-to-api calls work):

1. Read the JWT header to get its `kid` (key id).
2. Fetch (and cache, module-level) the Cognito JWKS.
3. Find the matching public key; unknown `kid` → `401`.
4. `jwt.decode` verifying signature (`RS256`), `iss == cognito_issuer`, and expiry
   (`audience` is **not** checked — Cognito access tokens carry no `aud`). Any
   `JWTError` (bad signature, wrong issuer, expired, malformed) → `401`.
5. Require `token_use == "access"` (id tokens are for the frontend, not the API).
6. If `cognito_allowed_client_ids` is set, require the token's `client_id` to be on
   it (defense in depth). A missing token → `401 Not authenticated`.

The decoded claim set is returned and made available to handlers, which authorize on
identity (`sub`) and `scope`.

> **api-to-api (user-less):** the same `require_auth` accepts a machine token as long
> as it's a valid access token from the pool. For dedicated service-to-service auth,
> add a Cognito **resource server + custom scopes** and a confidential
> **`client_credentials`** client per service, then authorize on those scopes.

### Declaring public vs protected routes

This is deliberate and per-route — there is **no global middleware**.

```python
# Protected: every route on the router requires a valid token.
router = APIRouter(prefix="/items", dependencies=[Depends(require_auth)])

# A handler that needs the caller's identity re-declares the dependency;
# FastAPI caches it within the request, so it runs only once.
@router.get("")
async def list_items(user: dict = Depends(require_auth)): ...

# Public: just omit the dependency.
router = APIRouter()
@router.get("/health")
async def health(): ...
```

## Endpoints

| Method & path | Auth | Returns |
|---|---|---|
| `GET /health` | public | `{"status": "ok"}` — liveness probe used by the ALB health check and the dashboard heartbeat. Cheap and **DB-independent** by design |
| `GET /health/db` | public | Readiness probe for the database: `{"status": "ok"}`, `{"status": "disabled"}` (no `DATABASE_URL`), or `{"status": "error", "detail"}` with HTTP `503` when configured but unreachable |
| `GET /whoami` | protected | `{"sub", "email", "claims"}` derived from the token (stub user in local dev) |
| `GET /items` | protected | List of example items |
| `GET /items/{item_id}` | protected | A single example item (typed `int` id) |

`/health/db` is kept **separate** from `/health` on purpose: the ALB liveness probe
must not depend on the database, or a transient DB outage would fail the probe and
cycle every API task. It runs a `SELECT 1` via `db.session.check_connection()` and
only ever exposes the exception *class name* (never the message or connection string)
on failure.

The `/items` and `/whoami` handlers return stub data — replace them with real queries
using `get_db`.

## Moodboard API

The API's real purpose: an **agentic moodboard service** that other AIs and products
call. Two capabilities, each usable entirely on its own.

### A. Briefing (`/briefs`) — agentic, multi-step

Walks a caller through building a moodboard brief: a fixed backbone of stages
(`work → feeling → references → palette → audience`) with one optional agent-inserted
follow-up per stage, and inline "forks" (alternatives) that resolve into divergent
**directions**. Server-authoritative, so the SPA and external clients share one flow.

| Method & path | Returns |
|---|---|
| `POST /briefs` | Create a session → `{id, status, next_question, content}` |
| `POST /briefs/{id}/answer` | Record the current answer (`value` / `options` (fork) / `skip`); returns the next question, an adaptive follow-up, or `next_question: null` when done |
| `POST /briefs/{id}/directions` | Curate divergent directions from the forks; session → `ready` |
| `GET /briefs/{id}` | Full persisted state |

### B. Generation (`/moodboards`) — async, image + HTML

Composes a concept + image prompts (LLM), renders tiles (image provider), and assembles
a **self-contained HTML file** (images inlined as data URIs). Accepts **either** a saved
`brief_id` **or** an inline `brief` payload — so a client can generate without ever
briefing. One request fans out to one moodboard per direction.

| Method & path | Returns |
|---|---|
| `POST /moodboards` | Start generation (`{brief_id}` or `{brief}` + optional `directions`) → `202` `{id, status, moodboards:[…]}` |
| `GET /moodboards/requests/{id}` | Request status + per-moodboard status |
| `GET /moodboards/requests/{id}/events` | **SSE** stream of progress, closing on a terminal status |
| `GET /moodboards/{id}` | One moodboard (concept, palette, image URLs, `html_url`) |
| `GET /moodboards/{id}/html` | The shareable self-contained HTML (auth-gated) |
| `GET /moodboards/{id}/image/{n}` | A rendered tile (local storage backend) |

Generation runs as a FastAPI **background task**; clients watch progress over **SSE**
(`status → done`). All routes are protected and scoped to the caller's `sub`
(cross-service tokens work).

### Providers (pluggable, with local stubs)

| Concern | Real | Stub (when unset) | Config |
|---|---|---|---|
| LLM (follow-ups, concept + prompts) | Anthropic / Claude `claude-opus-4-8` | deterministic | `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` |
| Image rendering | Replicate (`black-forest-labs/flux-dev`) | deterministic SVG | `REPLICATE_API_TOKEN`, `REPLICATE_MODEL` |
| Asset storage | S3 | local filesystem | `S3_BUCKET`, `S3_PREFIX`, `STORAGE_DIR` |

Each real provider is **lazy-imported** inside its adapter, so the app imports and the
test suite runs with none of these installed/configured — the stubs make the whole
pipeline hermetic (the same philosophy as `LOCAL_DEV`). See `.env.example`.

### Persistence

`brief_sessions`, `generation_requests`, and `moodboards` (migration `0002`). Requests
and moodboards persist so a slow/failed async run can be streamed and the result
revisited later. **Known limitations** (see [TODO.md](../TODO.md)): the worker is
in-process (lost on restart; single-instance SSE), and the HTML share route is auth-gated
pending a shared cross-service "store & share" workflow.

## Database layer

The DB layer is present but **dormant** by default — the API runs without a
`DATABASE_URL`. When you need persistence:

* `db/session.py` lazily creates the async engine on first use; calling `get_db()`
  without `DATABASE_URL` set raises a clear `RuntimeError`.
* Models go in `app/models/` and **must be re-exported from `app/models/__init__.py`**.
  Alembic's `env.py` does `import app.models` before autogenerate, so a model that
  isn't re-exported is invisible to migrations. `test_db.py` guards this.

### Migrations (Alembic)

* `alembic/env.py` runs migrations against `settings.database_url`, but only overrides
  the URL when it's actually set — so tests can inject a throwaway SQLite URL via the
  Alembic `Config`.
* Run inside the container:

  ```bash
  docker compose exec api uv run alembic upgrade head      # apply
  docker compose exec api uv run alembic revision --autogenerate -m "add foo"
  docker compose exec api uv run alembic downgrade base    # tear down
  ```

## Running the API locally

```bash
docker compose up api postgres        # API on :8000, Postgres on :5432
# or, without Docker, from apps/api:
uv sync --extra dev
uv run uvicorn app.main:app --reload
```

## Tests

See [testing.md](testing.md). In short: `docker compose exec api uv run pytest`.
