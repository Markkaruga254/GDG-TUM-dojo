import { defineConfig, devices } from "@playwright/test";

import { BACKEND_URL, BASE_URL, MOCK_GITHUB_URL } from "./support/env";

/**
 * The suite runs the real stack on dedicated ports so it never collides with a
 * development server: frontend 5174, backend 8002, mock GitHub API 8990.
 * `npm run seed` prepares the disposable database before the servers start.
 */
export default defineConfig({
  testDir: "./tests",
  // Tests share one seeded database and run against it in order (01 → 04).
  fullyParallel: false,
  workers: 1,
  forbidOnly: Boolean(process.env.CI),
  retries: 0,
  timeout: 60_000,
  expect: { timeout: 15_000 },
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : [["list"]],
  use: {
    baseURL: BASE_URL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: "node scripts/mock-github.mjs",
      url: `${MOCK_GITHUB_URL}/health`,
      reuseExistingServer: false,
      timeout: 30_000,
    },
    {
      command: "node scripts/start-backend.mjs",
      url: `${BACKEND_URL}/health`,
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: "npm run dev -- --host 127.0.0.1 --port 5174 --strictPort",
      cwd: "../frontend",
      env: { VITE_API_PROXY_TARGET: BACKEND_URL },
      url: BASE_URL,
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
});
