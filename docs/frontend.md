# Frontend (React + Vite)

The frontend lives in [apps/frontend](../apps/frontend). It is a React 18 + Vite +
TypeScript SPA using React Router, TanStack Query for data fetching, and **CSS Modules
only** for styling (no Tailwind, no CSS-in-JS).

## Structure

```
src/
├── main.tsx            Mounts <App>; imports global.css
├── App.tsx             Providers (QueryClient, AuthProvider) + routes
├── auth/
│   ├── cognito.ts      PKCE helpers + OAuth2 token endpoints
│   └── AuthContext.tsx Auth state, token storage, silent refresh
├── api/
│   └── client.ts       QueryClient config + fetchWithAuth()
├── components/
│   ├── ProtectedRoute.tsx  Gate that redirects unauthenticated users to /login
│   └── Modal.tsx           Accessible dialog (Escape / backdrop to close)
├── pages/
│   ├── Login.tsx       "Continue with Cognito" button
│   ├── Callback.tsx    Exchanges ?code=… for tokens
│   └── Home.tsx        The status dashboard (default route)
└── styles/
    ├── tokens.css      Design tokens (CSS custom properties)
    └── global.css      Base styles built on the tokens
```

## Routes

| Path | Component | Notes |
|---|---|---|
| `/` | `Home` | Wrapped in `ProtectedRoute` |
| `/login` | `Login` | Redirects to `/` if already authenticated |
| `/callback` | `Callback` | OAuth2 redirect target |

## Auth flow

Configured entirely through `VITE_`-prefixed env vars (baked in at build time).

**Local dev (`VITE_LOCAL_DEV=true`):** `AuthProvider` boots already authenticated with a
stub `local-dev-token`; no Cognito interaction occurs. This mirrors the API's
`LOCAL_DEV` bypass and is what the e2e tests rely on.

**Production:**

1. `ProtectedRoute` sees the user isn't authenticated → renders `<Navigate to="/login">`.
2. `Login` calls `redirectToLogin()` (`auth/cognito.ts`), which generates a PKCE
   verifier/challenge, stashes the verifier in `sessionStorage`, and redirects to the
   Cognito Hosted UI `/oauth2/authorize` endpoint.
3. Cognito redirects to `/callback?code=…`. `Callback` calls `exchangeCodeForTokens`,
   which POSTs to `/oauth2/token` with the PKCE verifier.
4. `AuthProvider.setTokens` stores the refresh token in `localStorage` and schedules a
   silent refresh 60s before access-token expiry.
5. On reload, `AuthProvider` attempts to restore the session from the stored refresh
   token.

`fetchWithAuth(path, accessToken)` (`api/client.ts`) attaches
`Authorization: Bearer <accessToken>` and throws on non-2xx responses.

## The status dashboard (`Home.tsx`)

The default page is a developer dashboard that makes the template's wiring visible at a
glance. It runs four live checks, each opening a detail modal:

| Check | What it does |
|---|---|
| **API heartbeat** | Polls `GET /health` every 10s and reports round-trip latency |
| **Authentication** | Shows whether you're signed in and via what (Cognito vs local-dev bypass); decodes the access-token JWT **client-side** when present |
| **Identity (/whoami)** | Calls `GET /whoami` with the bearer token; a success proves the **API** validated the token and resolved your identity **server-side** (complements the client-side decode in Authentication) |
| **Protected API access** | Calls `GET /items` with the bearer token and reports how many items came back |

An **Environment** card shows the local-dev flag, Vite build mode, API base URL, and
Cognito domain. These behaviours are exactly what the Playwright suite asserts — see
[testing.md](testing.md).

## Environment variables

| Var | Used for |
|---|---|
| `VITE_LOCAL_DEV` | `true` bypasses auth in the SPA |
| `VITE_API_BASE_URL` | Base URL the dashboard calls (`""` = same origin) |
| `VITE_COGNITO_DOMAIN` | Cognito Hosted UI domain |
| `VITE_COGNITO_CLIENT_ID` | App-client id (PKCE) |
| `VITE_COGNITO_USER_POOL_ID` | User pool id |
| `VITE_COGNITO_REDIRECT_URI` | OAuth2 callback (`…/callback`) |

`VITE_` vars are **build-time** — the production Dockerfile takes them as build args and
`deploy.sh` passes them in.

## Running locally

```bash
docker compose up frontend            # http://localhost:5173
# or, from apps/frontend:
npm install && npm run dev
```
