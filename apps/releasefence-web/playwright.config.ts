import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  workers: 1,
  retries: 0,
  timeout: 45_000,
  reporter: [
    ["list"],
    ["junit", { outputFile: process.env.RELEASEFENCE_BROWSER_JUNIT }],
  ],
  outputDir: process.env.RELEASEFENCE_BROWSER_OUTPUT || "test-results",
  use: {
    baseURL: process.env.RELEASEFENCE_BROWSER_URL,
    channel: "chrome",
    headless: true,
    viewport: { width: 1440, height: 1000 },
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
});
