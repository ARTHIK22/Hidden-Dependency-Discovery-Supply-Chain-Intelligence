import { defineConfig } from "@playwright/test";
import { existsSync } from "node:fs";
import { resolve } from "node:path";

const frontendRoot = process.cwd();
const backendRoot = resolve(frontendRoot, "../backend");
const windows = process.platform === "win32";
const python = windows
  ? resolve(backendRoot, ".venv/Scripts/python.exe")
  : resolve(backendRoot, ".venv/bin/python");
const npm = windows ? "npm.cmd" : "npm";
const installedChrome = "C:/Program Files/Google/Chrome/Application/chrome.exe";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  timeout: 180_000,
  expect: { timeout: 15_000 },
  reporter: "list",
  use: {
    baseURL: "http://localhost:5175",
    browserName: "chromium",
    headless: true,
    launchOptions: existsSync(installedChrome) ? { executablePath: installedChrome } : {},
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: [
    {
      cwd: backendRoot,
      url: "http://localhost:8001/api/health",
      env: {
        DEMO_MODE: "true",
        APP_ENV: "development",
        CORS_ORIGINS: "http://localhost:5175,http://127.0.0.1:5175",
        HDI_E2E_FIXTURES: "true",
      },
      command: `"${python}" e2e_server.py`,
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: `${npm} run dev -- --host 0.0.0.0 --port 5175 --strictPort`,
      cwd: frontendRoot,
      url: "http://localhost:5175",
      env: {
        VITE_API_BASE_URL: "http://localhost:8001/api",
        VITE_WS_URL: "ws://localhost:8001/ws",
        VITE_APP_ENV: "development",
      },
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
