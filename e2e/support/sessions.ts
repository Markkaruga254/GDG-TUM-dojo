/**
 * Session bootstrap for the end-to-end suite.
 *
 * GitHub OAuth cannot run locally or in CI, so the suite injects the session
 * cookies that `backend/scripts/seed_e2e.py` minted for the disposable E2E
 * database. The tokens live in `e2e/.sessions.json` (gitignored) and are never
 * printed. `npm run seed` must run before the tests.
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { test as base } from "@playwright/test";
import type { Browser, BrowserContext, Page } from "@playwright/test";

import { BASE_URL, COOKIE_DOMAIN, CSRF_COOKIE, SESSION_COOKIE } from "./env";

export type Role = "admin" | "moderator" | "student" | "student2";

interface StoredSession {
  username: string;
  session: string;
  csrf: string;
}

type StoredSessions = Record<Role, StoredSession>;

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SESSIONS_PATH = process.env.E2E_SESSIONS_FILE ?? path.resolve(HERE, "..", ".sessions.json");

function loadSessions(): StoredSessions {
  if (!fs.existsSync(SESSIONS_PATH)) {
    throw new Error(
      `E2E sessions file not found at ${SESSIONS_PATH}. ` +
        'Run "npm run seed" from the e2e/ directory first.',
    );
  }
  return JSON.parse(fs.readFileSync(SESSIONS_PATH, "utf8")) as StoredSessions;
}

const sessions = loadSessions();

/** New browser context with the seeded session cookies for `role`. */
export async function sessionContext(browser: Browser, role: Role): Promise<BrowserContext> {
  const stored = sessions[role];
  if (!stored) {
    throw new Error(`No stored session for role "${role}" in ${SESSIONS_PATH}.`);
  }
  const context = await browser.newContext({ baseURL: BASE_URL });
  await context.addCookies([
    { name: SESSION_COOKIE, value: stored.session, domain: COOKIE_DOMAIN, path: "/" },
    { name: CSRF_COOKIE, value: stored.csrf, domain: COOKIE_DOMAIN, path: "/" },
  ]);
  return context;
}

/**
 * Extended test with per-role pages. Use `asStudent` / `asModerator` to land in
 * a signed-in session; the default `page` fixture stays anonymous.
 */
export const test = base.extend<{
  asStudent: Page;
  asModerator: Page;
}>({
  asStudent: async ({ browser }, use) => {
    const context = await sessionContext(browser, "student");
    const page = await context.newPage();
    await use(page);
    await context.close();
  },
  asModerator: async ({ browser }, use) => {
    const context = await sessionContext(browser, "moderator");
    const page = await context.newPage();
    await use(page);
    await context.close();
  },
});

export { expect } from "@playwright/test";
