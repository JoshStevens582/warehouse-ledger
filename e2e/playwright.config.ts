import path from "node:path";
import { fileURLToPath } from "node:url";

import { defineConfig, devices } from "@playwright/test";

const e2eDir = path.dirname(fileURLToPath(import.meta.url));
const ledgerRoot = path.join(e2eDir, "..");

const databaseUrl =
  process.env.DATABASE_URL ??
  "postgresql+psycopg://ledger:ledger@localhost:5432/warehouse_ledger";

const apiEnv: Record<string, string> = {
  DATABASE_URL: databaseUrl,
  REDIS_URL: process.env.REDIS_URL ?? "redis://localhost:6379/0",
  JWT_SECRET: process.env.JWT_SECRET ?? "e2e-secret",
  PAYSTACK_SECRET_KEY: process.env.PAYSTACK_SECRET_KEY ?? "sk_test_e2e",
};

export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: "http://127.0.0.1:5173",
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: "uv run uvicorn warehouse_ledger.main:app --host 127.0.0.1 --port 8080",
      cwd: ledgerRoot,
      url: "http://127.0.0.1:8080/api/health",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: apiEnv,
    },
    {
      command: "npm run dev -- --host 127.0.0.1 --port 5173",
      cwd: path.join(ledgerRoot, "frontend"),
      url: "http://127.0.0.1:5173",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
});