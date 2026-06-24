import { expect, test } from "@playwright/test";
import {
  mockApiHealthy,
  mockDbDown,
  mockDbHealthy,
  mockHealthDown,
  mockHealthy,
  mockItems,
  mockItemsError,
  mockWhoami,
  mockWhoamiError,
} from "./helpers";

/**
 * The home dashboard is the first thing a developer sees after cloning the
 * template. It surfaces live health checks (API heartbeat, database connection,
 * authentication, protected API access) plus an environment summary. These tests
 * assert each of those reflects the underlying state correctly.
 *
 * Auth is bypassed (local-dev mode), so navigating to "/" lands on the dashboard
 * without a Cognito round-trip. The backend is mocked per-test.
 */

test.describe("home dashboard", () => {
  test("renders the system status checks", async ({ page }) => {
    await mockApiHealthy(page);
    await page.goto("/");

    await expect(
      page.getByRole("heading", { name: "agent-moodboard", level: 1 }),
    ).toBeVisible();
    await expect(page.getByText("API heartbeat")).toBeVisible();
    await expect(page.getByText("Database connection")).toBeVisible();
    await expect(page.getByText("Authentication")).toBeVisible();
    await expect(page.getByText("Identity (/whoami)")).toBeVisible();
    await expect(page.getByText("Protected API access")).toBeVisible();
  });

  test("heartbeat reports OK when the API responds", async ({ page }) => {
    await mockApiHealthy(page);
    await page.goto("/");

    const row = page.getByRole("button", { name: /API heartbeat/ });
    await expect(row.getByText("OK", { exact: true })).toBeVisible();
    await expect(row).toContainText(/Responded in \d+ ms/);
  });

  test("heartbeat reports Down when the API is unreachable", async ({ page }) => {
    await mockHealthDown(page);
    await mockItems(page);
    await page.goto("/");

    const row = page.getByRole("button", { name: /API heartbeat/ });
    await expect(row.getByText("Down", { exact: true })).toBeVisible();
    await expect(row).toContainText("No response from the API");
  });

  test("database connection reports OK when the API can reach the DB", async ({
    page,
  }) => {
    await mockHealthy(page);
    await mockDbHealthy(page);
    await page.goto("/");

    const row = page.getByRole("button", { name: /Database connection/ });
    await expect(row.getByText("OK", { exact: true })).toBeVisible();
    await expect(row).toContainText(/Connected in \d+ ms/);
  });

  test("database connection reports Down when the DB is unreachable", async ({
    page,
  }) => {
    await mockHealthy(page);
    await mockDbDown(page);
    await page.goto("/");

    const row = page.getByRole("button", { name: /Database connection/ });
    await expect(row.getByText("Down", { exact: true })).toBeVisible();
    await expect(row).toContainText("Configured but unreachable");
  });

  test("authentication shows the local-dev bypass session", async ({ page }) => {
    await mockApiHealthy(page);
    await page.goto("/");

    const row = page.getByRole("button", { name: /Authentication/ });
    await expect(row.getByText("OK", { exact: true })).toBeVisible();
    await expect(row).toContainText("Local dev session (auth bypassed)");
  });

  test("identity resolves the caller via the API", async ({ page }) => {
    await mockHealthy(page);
    await mockItems(page);
    await mockWhoami(page, {
      sub: "abc-123",
      email: "alice@example.com",
      claims: { sub: "abc-123", email: "alice@example.com" },
    });
    await page.goto("/");

    const row = page.getByRole("button", { name: /Identity/ });
    await expect(row.getByText("OK", { exact: true })).toBeVisible();
    await expect(row).toContainText("Resolved as alice@example.com");
  });

  test("identity reports failure when /whoami is rejected", async ({ page }) => {
    await mockHealthy(page);
    await mockItems(page);
    await mockWhoamiError(page);
    await page.goto("/");

    const row = page.getByRole("button", { name: /Identity/ });
    await expect(row.getByText("Down", { exact: true })).toBeVisible();
    await expect(row).toContainText(/token rejected or API down/);
  });

  test("protected API access reports the number of items returned", async ({
    page,
  }) => {
    await mockHealthy(page);
    await mockItems(page, [
      { id: 1, name: "Alpha", description: null },
      { id: 2, name: "Beta", description: "second" },
    ]);
    await page.goto("/");

    const row = page.getByRole("button", { name: /Protected API access/ });
    await expect(row.getByText("OK", { exact: true })).toBeVisible();
    await expect(row).toContainText("Authorized — 2 items returned");
  });

  test("protected API access reports failure when the request is rejected", async ({
    page,
  }) => {
    await mockHealthy(page);
    await mockItemsError(page);
    await page.goto("/");

    const row = page.getByRole("button", { name: /Protected API access/ });
    await expect(row.getByText("Down", { exact: true })).toBeVisible();
    await expect(row).toContainText(/token rejected or API down/);
  });

  test("environment card reflects local-dev configuration", async ({ page }) => {
    await mockApiHealthy(page);
    await page.goto("/");

    const card = page
      .locator("section")
      .filter({ has: page.getByRole("heading", { name: "Environment" }) });
    await expect(card).toContainText("Local dev mode");
    await expect(card).toContainText("On");
    await expect(card).toContainText("http://localhost:8000");
  });
});
