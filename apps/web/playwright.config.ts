import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3100";
const skipWebServer = process.env.PLAYWRIGHT_SKIP_WEBSERVER === "1";
const reuseExistingServer = process.env.PLAYWRIGHT_REUSE_SERVER === "1";
// Routes are fully mocked and animations are disabled, so a 1% difference is
// already meaningful. The old 5% local / 25% CI threshold let an entire narrow
// mobile panel remain broken while the screenshot test stayed green.
const maxDiffPixelRatio = 0.01;
const serverURL = new URL(baseURL);
const serverPort = serverURL.port || (serverURL.protocol === "https:" ? "443" : "80");

export default defineConfig({
  testDir: "./e2e",
  snapshotPathTemplate: "{testDir}/__screenshots__/{projectName}/{arg}{ext}",
  timeout: 60_000,
  expect: {
    timeout: 10_000,
    toHaveScreenshot: {
      animations: "disabled",
      maxDiffPixelRatio,
    },
  },
  fullyParallel: false,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL,
    trace: "on-first-retry",
    timezoneId: "Asia/Ho_Chi_Minh",
    // Page routes mock every backend dependency. A registered PWA service
    // worker can bypass Playwright routing and make a visual test depend on a
    // real localhost API, so block it in this deterministic harness.
    serviceWorkers: "block",
  },
  projects: [
    {
      name: "desktop",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 1000 } },
    },
    {
      name: "mobile",
      use: { ...devices["Pixel 7"], viewport: { width: 412, height: 915 } },
    },
  ],
  webServer: skipWebServer
    ? undefined
    : {
        command: `npm run dev -- --hostname ${serverURL.hostname} --port ${serverPort}`,
        url: baseURL,
        env: { NEXT_PUBLIC_API_BASE_URL: baseURL },
        // Opt-in only. Reusing an unrelated `next dev` process made visual
        // tests pass against stale code while the current mobile UI was broken.
        reuseExistingServer,
        timeout: 120_000,
      },
});
