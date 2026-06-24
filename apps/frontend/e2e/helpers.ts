import type { Page } from "@playwright/test";

/**
 * Test helpers for mocking the backend API the dashboard talks to.
 *
 * The frontend issues requests to `${VITE_API_BASE_URL}/health` and `/items`. These
 * helpers intercept those calls so each test can pin the API to a known state
 * (healthy, down, returning specific items) without a live backend.
 */

export interface Item {
  id: number;
  name: string;
  description: string | null;
}

export interface WhoAmI {
  sub: string | null;
  email: string | null;
  claims: Record<string, unknown>;
}

const DEFAULT_ITEMS: Item[] = [
  { id: 1, name: "Example item", description: "Replace with DB query" },
];

const DEFAULT_WHOAMI: WhoAmI = {
  sub: "local-dev-user",
  email: "dev@local",
  claims: { sub: "local-dev-user", email: "dev@local" },
};

/** Mock `GET /health` to succeed (the API is up). */
export async function mockHealthy(page: Page): Promise<void> {
  await page.route("**/health", (route) =>
    route.fulfill({ json: { status: "ok" } }),
  );
}

/** Mock `GET /health` to fail (the API is unreachable). */
export async function mockHealthDown(page: Page): Promise<void> {
  await page.route("**/health", (route) => route.abort("failed"));
}

/** Mock `GET /health/db` to report the database is connected. */
export async function mockDbHealthy(page: Page): Promise<void> {
  await page.route("**/health/db", (route) =>
    route.fulfill({ json: { status: "ok" } }),
  );
}

/** Mock `GET /health/db` to report the database is configured but unreachable. */
export async function mockDbDown(page: Page): Promise<void> {
  await page.route("**/health/db", (route) =>
    route.fulfill({
      status: 503,
      json: { status: "error", detail: "ConnectionRefusedError" },
    }),
  );
}

/** Mock `GET /health/db` to report no database is configured (dormant DB layer). */
export async function mockDbDisabled(page: Page): Promise<void> {
  await page.route("**/health/db", (route) =>
    route.fulfill({ json: { status: "disabled" } }),
  );
}

/** Mock `GET /items` to return the given items (defaults to one example item). */
export async function mockItems(
  page: Page,
  items: Item[] = DEFAULT_ITEMS,
): Promise<void> {
  await page.route("**/items", (route) => route.fulfill({ json: items }));
}

/** Mock `GET /items` to fail (e.g. token rejected or API down). */
export async function mockItemsError(page: Page): Promise<void> {
  await page.route("**/items", (route) =>
    route.fulfill({ status: 401, body: "Unauthorized" }),
  );
}

/** Mock `GET /whoami` to return the given identity (defaults to the local-dev user). */
export async function mockWhoami(
  page: Page,
  whoami: WhoAmI = DEFAULT_WHOAMI,
): Promise<void> {
  await page.route("**/whoami", (route) => route.fulfill({ json: whoami }));
}

/** Mock `GET /whoami` to fail (e.g. token rejected or API down). */
export async function mockWhoamiError(page: Page): Promise<void> {
  await page.route("**/whoami", (route) =>
    route.fulfill({ status: 401, body: "Unauthorized" }),
  );
}

/** Apply the common "everything healthy" mocks in one call. */
export async function mockApiHealthy(page: Page): Promise<void> {
  await mockHealthy(page);
  await mockDbHealthy(page);
  await mockWhoami(page);
  await mockItems(page);
}
