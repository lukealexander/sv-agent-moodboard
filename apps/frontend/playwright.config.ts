import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright config for the frontend end-to-end suite.
 *
 * The tests boot the real Vite dev server in **local-dev mode**
 * (`VITE_LOCAL_DEV=true`), so Cognito auth is bypassed and the app renders the
 * dashboard directly. Backend calls (`/health`, `/items`) are mocked per-test with
 * `page.route`, which keeps the suite hermetic — no Postgres or running API needed —
 * and lets each test drive success/failure states deterministically.
 *
 * To run against a *real* backend instead, start `docker compose up`, drop the route
 * mocks in the relevant test, and point `VITE_API_BASE_URL` at the API.
 */

const PORT = 5173;
const BASE_URL = `http://localhost:${PORT}`;

export default defineConfig({
  testDir: "./e2e",
  // Fail the build on CI if test.only is committed by mistake.
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? [["html", { open: "never" }], ["list"]] : "list",

  use: {
    baseURL: BASE_URL,
    trace: "on-first-retry",
  },

  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],

  // Start the dev server before the suite; reuse a running one locally.
  webServer: {
    command: "npm run dev",
    url: BASE_URL,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    env: {
      VITE_LOCAL_DEV: "true",
      VITE_API_BASE_URL: "http://localhost:8000",
    },
  },
});
