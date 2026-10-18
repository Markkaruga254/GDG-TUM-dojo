/**
 * Shared helpers for the E2E scripts: resolve the backend Python interpreter
 * (virtualenv first, then PATH) and the disposable database URL.
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const E2E_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
export const BACKEND_DIR = path.resolve(E2E_DIR, "..", "backend");

const DEFAULT_DATABASE_URL =
  "postgresql+psycopg://buildarena:buildarena@127.0.0.1:5433/buildarena_e2e";

export function resolvePython() {
  const venvPython = path.join(BACKEND_DIR, ".venv", "bin", "python");
  return fs.existsSync(venvPython) ? venvPython : "python3";
}

export function databaseUrl() {
  return process.env.E2E_DATABASE_URL ?? DEFAULT_DATABASE_URL;
}
