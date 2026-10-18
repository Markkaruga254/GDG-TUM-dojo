#!/usr/bin/env node
/**
 * Prepares the disposable E2E database before the suite runs:
 *
 *   1. create the database when it is missing (via the seed script);
 *   2. apply migrations (alembic upgrade head);
 *   3. seed deterministic users, challenges and one evaluated submission.
 *
 * Prerequisites: PostgreSQL reachable via E2E_DATABASE_URL (default
 * buildarena_e2e on port 5433) and the backend dependencies installed
 * (backend/.venv or a Python on PATH with the project installed).
 */

import { spawnSync } from "node:child_process";

import { BACKEND_DIR, databaseUrl, resolvePython } from "./python.mjs";

const python = resolvePython();
const env = { ...process.env, DATABASE_URL: databaseUrl() };

function run(args) {
  const result = spawnSync(python, args, { cwd: BACKEND_DIR, env, stdio: "inherit" });
  if (result.error) {
    console.error(`failed to run ${python}: ${result.error.message}`);
    process.exit(1);
  }
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

run(["-m", "scripts.seed_e2e", "--ensure-database"]);
run(["-m", "alembic", "upgrade", "head"]);
run(["-m", "scripts.seed_e2e"]);

console.log("E2E database ready.");
