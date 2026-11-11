import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "tests",
  testMatch: "**/*.e2e.ts",
  use: {
    baseURL: process.env.DRAFTROOM_TEST_URL ?? "http://127.0.0.1:3030",
    headless: true,
    launchOptions: { executablePath: process.env.DRAFTROOM_BROWSER },
    viewport: { width: 1440, height: 1100 },
  },
  reporter: "list",
});
