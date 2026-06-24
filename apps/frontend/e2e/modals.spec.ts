import { expect, test } from "@playwright/test";
import { mockApiHealthy, mockHealthy, mockItems } from "./helpers";

/**
 * Each status row opens a detail modal explaining what was checked, the endpoint
 * involved, and the raw response. These tests cover the modal interactions:
 * opening, content, and the two ways to close (the ✕ button and the Escape key).
 */

test.describe("status detail modals", () => {
  test.beforeEach(async ({ page }) => {
    await mockApiHealthy(page);
    await page.goto("/");
  });

  test("heartbeat modal shows the health endpoint and response", async ({
    page,
  }) => {
    await page.getByRole("button", { name: /API heartbeat/ }).click();

    const dialog = page.getByRole("dialog", { name: "API heartbeat" });
    await expect(dialog).toBeVisible();
    await expect(dialog).toContainText("/health");
    await expect(dialog).toContainText('"status": "ok"');
  });

  test("database modal shows the readiness probe and connection status", async ({
    page,
  }) => {
    await page.getByRole("button", { name: /Database connection/ }).click();

    const dialog = page.getByRole("dialog", { name: "Database connection" });
    await expect(dialog).toBeVisible();
    await expect(dialog).toContainText("/health/db");
    await expect(dialog).toContainText("Connected");
    await expect(dialog).toContainText("SELECT 1");
  });

  test("auth modal explains the local-dev bypass", async ({ page }) => {
    await page.getByRole("button", { name: /Authentication/ }).click();

    const dialog = page.getByRole("dialog", { name: "Authentication" });
    await expect(dialog).toBeVisible();
    await expect(dialog).toContainText("Local dev (auth bypassed)");
    await expect(dialog).toContainText(/Running in local dev mode/);
  });

  test("identity modal shows the server-side claims from /whoami", async ({
    page,
  }) => {
    await page.getByRole("button", { name: /Identity/ }).click();

    const dialog = page.getByRole("dialog", { name: "Identity (/whoami)" });
    await expect(dialog).toBeVisible();
    await expect(dialog).toContainText("/whoami");
    await expect(dialog).toContainText("dev@local");
    await expect(dialog).toContainText("Claims (server-side)");
  });

  test("items modal lists the items returned by the API", async ({ page }) => {
    await mockItems(page, [
      { id: 7, name: "Gamma", description: "a described item" },
    ]);
    await page.reload();

    await page.getByRole("button", { name: /Protected API access/ }).click();

    const dialog = page.getByRole("dialog", { name: "Protected API access" });
    await expect(dialog).toBeVisible();
    await expect(dialog).toContainText("Gamma");
    await expect(dialog).toContainText("a described item");
  });

  test("modal closes via the close button", async ({ page }) => {
    await page.getByRole("button", { name: /API heartbeat/ }).click();
    const dialog = page.getByRole("dialog", { name: "API heartbeat" });
    await expect(dialog).toBeVisible();

    await dialog.getByRole("button", { name: "Close" }).click();
    await expect(dialog).toBeHidden();
  });

  test("modal closes when Escape is pressed", async ({ page }) => {
    await page.getByRole("button", { name: /Authentication/ }).click();
    const dialog = page.getByRole("dialog", { name: "Authentication" });
    await expect(dialog).toBeVisible();

    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden();
  });
});
