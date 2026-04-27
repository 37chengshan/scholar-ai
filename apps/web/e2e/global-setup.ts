/**
 * Playwright Global Setup
 *
 * Runs once before all tests. Ensures:
 * 1. Test user exists (via API).
 * 2. Logs in and saves storageState to e2e/.auth/user.json.
 * 3. All tests reuse this storageState — no per-test login needed.
 */
import { chromium, FullConfig } from '@playwright/test';
import { promises as fs } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const AUTH_FILE = path.resolve(__dirname, '.auth/user.json');

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:5173';

function buildE2EUser() {
  return {
    email: process.env.E2E_USER_EMAIL ?? 'pr19-e2e@example.com',
    password: process.env.E2E_USER_PASSWORD ?? 'Pr19E2EPass123',
  };
}

async function authFileValid(): Promise<boolean> {
  try {
    const content = await fs.readFile(AUTH_FILE, 'utf-8');
    const state = JSON.parse(content);
    // storageState has cookies array
    return Array.isArray(state?.cookies) && state.cookies.length > 0;
  } catch {
    return false;
  }
}

export default async function globalSetup(_config: FullConfig) {
  const user = buildE2EUser();

  // Reuse cached auth if still valid
  if (await authFileValid()) {
    console.log('[global-setup] Reusing cached auth state.');
    return;
  }

  console.log(`[global-setup] Logging in as ${user.email}…`);
  await fs.mkdir(path.dirname(AUTH_FILE), { recursive: true });

  const browser = await chromium.launch();
  const context = await browser.newContext({ baseURL: BASE_URL });
  const page = await context.newPage();

  await page.goto('/login');
  await page.fill('input[type="email"]', user.email);
  await page.fill('input[type="password"]', user.password);

  const submitButton = page.locator('button[type="submit"]').first();
  await submitButton.waitFor({ state: 'visible', timeout: 10000 });
  try {
    await submitButton.click({ timeout: 10000 });
  } catch {
    await page.locator('input[type="password"]').press('Enter');
  }

  try {
    await page.waitForURL(/\/dashboard/, { timeout: 25000 });
  } catch {
    await browser.close();
    throw new Error(
      `[global-setup] Login failed for ${user.email}. `
      + 'Ensure account exists: '
      + '`cd apps/api && python scripts/ensure_e2e_test_user.py`',
    );
  }

  await context.storageState({ path: AUTH_FILE });
  await browser.close();
  console.log(`[global-setup] Auth state saved to ${AUTH_FILE}`);
}
