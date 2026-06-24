import { defineConfig, devices } from "@playwright/test";

/**
 * E2E tests run against the Next.js dev server on localhost:3000.
 * Start the backend separately on localhost:8000 before running E2E tests,
 * or set NEXT_PUBLIC_API_URL to point at a test/staging backend.
 *
 * Run: npm run test:e2e
 * Run (headed): npm run test:e2e -- --headed
 * Run (specific file): npm run test:e2e -- e2e/jobs.spec.ts
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? "github" : "html",

  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "firefox",
      use: { ...devices["Desktop Firefox"] },
    },
    {
      name: "mobile-chrome",
      use: { ...devices["Pixel 5"] },
    },
  ],

  // Auto-start Next.js dev server when running locally.
  // Remove this block to run against an already-started server.
  webServer: {
    command: "npm run dev",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
