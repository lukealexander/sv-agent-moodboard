# TODOs

[ ] Write project spec
[ ] Review Copilot instructions file
[ ] Remove Postgres container if not needed
[ ] Copy .env.example to .env and set up variables
[ ] Add healthcheck endpoint and status for the main page
[ ] Change title of React app (if using)
[ ] Write new README.md file

# Moodboard API — follow-ups

[ ] Wire the frontend brief flow to the real API (replace the local mock agent in
    apps/frontend/src/features/brief with calls to /briefs and /moodboards + SSE).
[ ] Build a "your sessions" surface in the frontend to revisit past briefs and
    generated moodboards (the API already persists them; no UI yet).
[ ] Replace the auth-gated HTML route with the shared cross-microservice
    "store & share result" workflow once it exists (a public, token-based share link).
[ ] Production durability: the async generation worker runs in-process via FastAPI
    BackgroundTasks (lost on restart, single-instance). Move to a durable queue
    (SQS / arq) for at-least-once execution and multi-instance SSE (shared broker).

# Complete

[x] Add the agentic moodboard API: briefing (/briefs) + generation (/moodboards),
    persisted sessions/requests, Claude + Replicate providers (with local stubs),
    async generation with SSE progress, self-contained shareable HTML.

 