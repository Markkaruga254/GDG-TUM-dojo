#!/usr/bin/env node
/**
 * Starts the FastAPI backend for the E2E suite with a deterministic
 * environment: test settings (rate limits off), the disposable E2E database
 * and the mock GitHub API. Playwright's webServer launches this script.
 */

import { spawn } from "node:child_process";

import { BACKEND_DIR, databaseUrl, resolvePython } from "./python.mjs";

const PORT = Number(process.env.E2E_BACKEND_PORT ?? "8002");
const ORIGIN = process.env.E2E_BASE_URL ?? "http://127.0.0.1:5174";
const MOCK_GITHUB_URL = process.env.E2E_MOCK_GITHUB_URL ?? "http://127.0.0.1:8990";

const env = {
  ...process.env,
  ENVIRONMENT: "test",
  DATABASE_URL: databaseUrl(),
  GITHUB_API_BASE_URL: MOCK_GITHUB_URL,
  FRONTEND_ORIGINS: ORIGIN,
  BACKEND_BASE_URL: `http://127.0.0.1:${PORT}`,
  FRONTEND_AUTH_REDIRECT_URL: `${ORIGIN}/auth/callback`,
  LOG_LEVEL: process.env.E2E_LOG_LEVEL ?? "WARNING",
};

const child = spawn(
  resolvePython(),
  ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", String(PORT)],
  { cwd: BACKEND_DIR, env, stdio: "inherit" },
);

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => child.kill(signal));
}

child.on("exit", (code, signal) => {
  process.exit(code ?? (signal ? 1 : 0));
});
