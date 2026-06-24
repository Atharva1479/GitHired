import { expect, test } from "@playwright/test";

/**
 * Jobs page E2E tests.
 *
 * Prerequisites:
 *   - Backend running on NEXT_PUBLIC_API_URL (default: http://localhost:8000)
 *   - A seeded test user: TEST_USER_EMAIL / TEST_USER_PASSWORD env vars
 *
 * Run authenticated tests with:
 *   TEST_USER_EMAIL=test@example.com TEST_USER_PASSWORD=secret npm run test:e2e -- e2e/jobs.spec.ts
 */

// Helper: login via the UI and return once dashboard is visible
async function loginAs(
  page: import("@playwright/test").Page,
  email: string,
  password: string,
) {
  await page.goto("/login");
  await page.getByRole("textbox", { name: /email/i }).fill(email);
  await page.getByLabel(/password/i).fill(password);
  await page.getByRole("button", { name: /sign in|log in/i }).first().click();
  await page.waitForURL(/\/(dashboard|jobs|applications)/, { timeout: 10_000 });
}

const EMAIL = process.env.TEST_USER_EMAIL ?? "";
const PASSWORD = process.env.TEST_USER_PASSWORD ?? "";

test.describe("Jobs page — authenticated", () => {
  test.skip(!EMAIL || !PASSWORD, "Skipped: TEST_USER_EMAIL / TEST_USER_PASSWORD not set");

  test.beforeEach(async ({ page }) => {
    await loginAs(page, EMAIL, PASSWORD);
    await page.goto("/jobs");
  });

  test("renders the search input", async ({ page }) => {
    await expect(
      page.getByRole("textbox", { name: /search|job title|role/i }),
    ).toBeVisible();
  });

  test("searching for 'engineer' shows results", async ({ page }) => {
    await page.getByRole("textbox", { name: /search|job title|role/i }).fill("engineer");
    await page.keyboard.press("Enter");
    // Wait for at least one JobCard to appear
    await expect(
      page.locator("[data-testid='job-card'], button:has-text('Apply & Track')").first(),
    ).toBeVisible({ timeout: 15_000 });
  });

  test("freshness filter changes visible jobs without new network request", async ({ page }) => {
    await page.getByRole("textbox", { name: /search|job title|role/i }).fill("engineer");
    await page.keyboard.press("Enter");
    await page.getByRole("button", { name: /apply & track/i }).first().waitFor({ timeout: 15_000 });

    // Count fetch requests before changing filter
    let fetchCount = 0;
    page.on("request", (req) => {
      if (req.url().includes("/jobs/search")) fetchCount++;
    });

    const filterBtn = page.getByRole("button", { name: /6h|24h|72h|last/i }).first();
    if (await filterBtn.isVisible()) {
      await filterBtn.click();
    }
    // Give React time to update — no new network request should have fired
    await page.waitForTimeout(300);
    expect(fetchCount).toBe(0);
  });

  test("clicking a job card opens the preview panel", async ({ page }) => {
    await page.getByRole("textbox", { name: /search|job title|role/i }).fill("engineer");
    await page.keyboard.press("Enter");
    const firstCard = page
      .locator("h3")
      .filter({ hasText: /.+/ })
      .first();
    await firstCard.waitFor({ timeout: 15_000 });
    const jobTitle = await firstCard.textContent();
    await firstCard.click();
    // Preview panel should show the same title
    await expect(page.getByText(jobTitle!).last()).toBeVisible({ timeout: 5_000 });
  });
});

test.describe("Jobs page — unauthenticated", () => {
  test("redirects to login", async ({ page }) => {
    await page.goto("/jobs");
    await expect(page).toHaveURL(/\/login/);
  });
});
