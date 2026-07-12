import { defineConfig, devices } from "@playwright/test";

// E2E runs against a running app (npm run build && npm start, or a staging URL).
// Not part of the CI unit job; run locally/staging with `npm run test:e2e`.
export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  use: {
    baseURL: process.env.E2E_BASE_URL || "http://localhost:3000",
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
