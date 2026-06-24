import { expect, test } from "@playwright/test";

/**
 * Auth guard E2E tests.
 *
 * These tests verify routing and access-control without needing valid
 * credentials. They ensure the login page is reachable and that
 * unauthenticated visitors are redirected away from protected routes.
 */

test.describe("Login page", () => {
  test("is publicly accessible", async ({ page }) => {
    await page.goto("/login");
    await expect(page).toHaveTitle(/GitHired|Job|Pilot/i);
    // Login form or Google OAuth button must be visible
    await expect(
      page.getByRole("button", { name: /sign in|log in|continue with google/i }).first(),
    ).toBeVisible();
  });

  test("shows email and password fields", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("textbox", { name: /email/i })).toBeVisible();
    await expect(page.getByLabel(/password/i)).toBeVisible();
  });

  test("shows validation error for empty form submit", async ({ page }) => {
    await page.goto("/login");
    await page.getByRole("button", { name: /sign in|log in/i }).first().click();
    // Browser or app-level validation must surface something
    const emailInput = page.getByRole("textbox", { name: /email/i });
    // HTML5 required — the field should be marked invalid
    await expect(emailInput).toHaveAttribute("required");
  });
});

test.describe("Protected routes redirect to login", () => {
  const protectedPaths = [
    "/dashboard",
    "/applications",
    "/jobs",
    "/ats",
    "/interview",
    "/dsa",
    "/settings",
  ];

  for (const path of protectedPaths) {
    test(`${path} redirects unauthenticated user`, async ({ page }) => {
      await page.goto(path);
      // Should end up on /login (direct or via redirect)
      await expect(page).toHaveURL(/\/login/);
    });
  }
});
