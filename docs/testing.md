# Testing

The template ships two test suites:

* **API** — Pytest, in [apps/api/tests](../apps/api/tests). Unit/integration tests for
  the FastAPI app: health, auth enforcement, the example resource, `/whoami`, and the
  Alembic migration machinery.
* **Frontend e2e** — Playwright, in [apps/frontend/e2e](../apps/frontend/e2e). Browser
  tests that drive the real app and assert the status dashboard behaves correctly.

Both suites are **hermetic** — they need no real Cognito, and the e2e suite needs no
running backend. That's possible because both layers honour a local-dev bypass and the
e2e tests mock the API at the network boundary.

---

## API tests (Pytest)

### Running

```bash
# In the dev container / compose
docker compose exec api uv run pytest
docker compose exec api uv run pytest --cov        # with coverage

# Or from apps/api directly
uv sync --extra dev
uv run pytest -v
```

`pyproject.toml` sets `asyncio_mode = "auto"` and `testpaths = ["tests"]`.

### Layout

| File | Covers |
|---|---|
| `conftest.py` | Shared fixtures: `client`, `local_dev`, `production`, `cognito` (token factory) |
| `test_health.py` | `/health` is public and stable in both modes |
| `test_auth.py` | Auth enforcement: bypass in local dev; missing/malformed/expired/wrong-audience/unknown-key tokens rejected; valid token accepted |
| `test_items.py` | Example resource response shape and path-param validation |
| `test_whoami.py` | `/whoami` returns the stub user (local dev) and reflects token claims (prod) |
| `test_config.py` | CORS settings: wildcard in local dev; production refuses to boot without `CORS_ALLOWED_ORIGINS` |
| `test_db.py` | Migrations build/tear-down the schema; every model is registered on `Base.metadata` |

### How the two auth modes are simulated

`settings` is a singleton shared by every module (`from app.config import settings`).
Rather than reloading modules, fixtures mutate that one object with `monkeypatch`, which
flips behaviour everywhere and auto-reverts after the test:

* `local_dev` — sets `settings.local_dev = True` (auth bypassed).
* `production` — sets `local_dev = False` plus test Cognito ids, and clears the JWKS
  cache.

### Testing real token validation without Cognito

The `cognito` fixture makes the **production** validation path genuinely exercisable
offline:

1. A throwaway RSA keypair is generated (session-scoped — keygen is slow).
2. A JWKS is built from the public key and the module-level JWKS cache is pre-populated,
   so `require_auth` never hits the network.
3. The fixture returns a `make_token(**overrides)` factory that signs real `RS256`
   tokens. Tests forge edge cases by overriding claims/headers:

   ```python
   cognito()                          # valid token
   cognito(exp=0)                     # expired
   cognito(aud="some-other-client")   # wrong audience
   cognito(kid="unknown-kid")         # signing key not in JWKS
   ```

This means the auth tests run the actual signature/audience/expiry checks in
`app/dependencies/auth.py`, not a mock of them.

### Adding API tests

* Need a protected route reachable? Depend on the `cognito` fixture and pass
  `headers=auth_header(token)` (helper in `conftest.py`).
* Need DB access? Follow `test_db.py`: point Alembic at a `tmp_path` SQLite file.

---

## Frontend e2e tests (Playwright)

### Running

```bash
cd apps/frontend
npm install
npx playwright install chromium     # one-time browser download
npm run test:e2e                     # headless
npm run test:e2e:ui                  # interactive UI mode
npm run test:e2e:report              # open the last HTML report
```

`playwright.config.ts` starts the Vite dev server automatically (its `webServer`
block) with `VITE_LOCAL_DEV=true`, so auth is bypassed and `/` renders the dashboard
directly. `reuseExistingServer` is on locally and off in CI.

### Layout

| File | Covers |
|---|---|
| `e2e/helpers.ts` | `page.route` mocks for `/health` and `/items` (healthy / down / custom / error) |
| `e2e/dashboard.spec.ts` | Each status check reflects API state; the environment card |
| `e2e/modals.spec.ts` | Opening each detail modal, its contents, and closing (✕ and Escape) |

### Why the backend is mocked

The e2e suite tests **frontend behaviour**, so it intercepts the API at the network
boundary with `page.route`. This keeps the suite deterministic and self-contained — no
Postgres, no running API — and lets a single test pin the API to "down", "returns 2
items", or "rejects the token". Example:

```ts
await mockHealthy(page);                 // GET /health → 200 {status:"ok"}
await mockItems(page, [{ id: 1, name: "Alpha", description: null }]);
await page.goto("/");
```

To run the e2e suite against a **real** backend instead, `docker compose up`, remove
the relevant `mock*` calls, and point `VITE_API_BASE_URL` at the API.

### Adding e2e tests

Add a `*.spec.ts` under `e2e/`, set up the API state with the helpers (or add a new
helper), navigate, and assert with role-based locators (`getByRole`, `getByText`). Use
`{ exact: true }` on short badge text (`"OK"`, `"Down"`) to avoid matching substrings in
nearby copy.

---

## Continuous integration

Both suites are CI-ready:

* API: `uv sync --extra dev && uv run pytest` (no services required).
* e2e: `npm ci && npx playwright install --with-deps chromium && npm run test:e2e`.
  Playwright honours `CI=true` (retries, no server reuse, HTML report).
