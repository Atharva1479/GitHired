import path from "path";
import { expect, test } from "@playwright/test";

/**
 * ATS scorer E2E tests.
 *
 * Prerequisites:
 *   - Backend running with Gemini configured
 *   - TEST_USER_EMAIL / TEST_USER_PASSWORD set for authenticated tests
 *   - A small fixture PDF in e2e/fixtures/sample-resume.pdf
 */

const EMAIL = process.env.TEST_USER_EMAIL ?? "";
const PASSWORD = process.env.TEST_USER_PASSWORD ?? "";

async function loginAs(
  page: import("@playwright/test").Page,
  email: string,
  password: string,
) {
  await page.goto("/login");
  await page.getByRole("textbox", { name: /email/i }).fill(email);
  await page.getByLabel(/password/i).fill(password);
  await page.getByRole("button", { name: /sign in|log in/i }).first().click();
  await page.waitForURL(/\/(dashboard|jobs|applications|ats)/, { timeout: 10_000 });
}

test.describe("ATS scorer page — authenticated", () => {
  test.skip(!EMAIL || !PASSWORD, "Skipped: TEST_USER_EMAIL / TEST_USER_PASSWORD not set");

  test.beforeEach(async ({ page }) => {
    await loginAs(page, EMAIL, PASSWORD);
    await page.goto("/ats");
  });

  test("renders the resume upload input", async ({ page }) => {
    await expect(
      page.getByRole("button", { name: /upload|choose|browse/i }).first(),
    ).toBeVisible();
  });

  test("renders the JD text area or upload option", async ({ page }) => {
    // JD can be a textarea or a file input area
    const jdArea = page
      .getByRole("textbox", { name: /job description|paste jd/i })
      .or(page.getByText(/paste your job description/i))
      .first();
    await expect(jdArea).toBeVisible();
  });

  test("shows score gauge on the results page after analysis", async ({ page }) => {
    // Try to navigate to results if localStorage already has a result from a
    // previous run; otherwise this test is informational only.
    const hasResult = await page.evaluate(() => !!localStorage.getItem("ats_result"));
    test.skip(!hasResult, "No cached ATS result in localStorage — run a real analysis first");

    await page.goto("/ats/results");
    // Score gauge renders an SVG circle
    await expect(page.locator("svg circle").first()).toBeVisible({ timeout: 5_000 });
  });
});

test.describe("ATS scorer page — unauthenticated", () => {
  test("redirects to login", async ({ page }) => {
    await page.goto("/ats");
    await expect(page).toHaveURL(/\/login/);
  });

  test("results page redirects to login", async ({ page }) => {
    await page.goto("/ats/results");
    await expect(page).toHaveURL(/\/login/);
  });
});
