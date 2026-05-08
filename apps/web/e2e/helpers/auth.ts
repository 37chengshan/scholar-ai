import type { APIRequestContext, BrowserContext, Page } from '@playwright/test';
import { promises as fs } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

type E2EUser = {
  email: string;
  password: string;
  name: string;
};

type AuthCookie = Awaited<ReturnType<BrowserContext['cookies']>>[number];

type CachedAuthState = {
  user: E2EUser;
  cookies: AuthCookie[];
};

let cachedAuthState: CachedAuthState | null = null;
let cachedAuthStatePromise: Promise<CachedAuthState> | null = null;

const AUTH_STATE_PATH = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../.auth/e2e-auth-state.json');

function buildE2EUser(): E2EUser {
  return {
    email: process.env.E2E_USER_EMAIL ?? process.env.PR19_E2E_USER_EMAIL ?? 'pr19-e2e@example.com',
    password: process.env.E2E_USER_PASSWORD ?? process.env.PR19_E2E_USER_PASSWORD ?? 'Pr19E2EPass123',
    name: process.env.E2E_USER_NAME ?? 'PR19 E2E User',
  };
}

async function validateBrowserSession(page: Page): Promise<boolean> {
  await page.goto('/', { waitUntil: 'domcontentloaded' });

  try {
    return await page.evaluate(async () => {
      const authInit: RequestInit = { credentials: 'include' };

      const me = await fetch('/api/v1/auth/me', authInit);
      if (me.ok) {
        return true;
      }

      if (me.status !== 401) {
        return false;
      }

      const refresh = await fetch('/api/v1/auth/refresh', {
        ...authInit,
        method: 'POST',
      });

      if (!refresh.ok) {
        return false;
      }

      const meAfterRefresh = await fetch('/api/v1/auth/me', authInit);
      return meAfterRefresh.ok;
    });
  } catch {
    return false;
  }
}

async function readPersistedAuthState(): Promise<CachedAuthState | null> {
  try {
    const content = await fs.readFile(AUTH_STATE_PATH, 'utf-8');
    const parsed = JSON.parse(content) as Partial<CachedAuthState> & { cookies?: AuthCookie[] };
    if (!Array.isArray(parsed?.cookies) || parsed.cookies.length === 0) {
      return null;
    }
    return {
      user: buildE2EUser(),
      cookies: parsed.cookies,
    };
  } catch {
    return null;
  }
}

async function persistAuthState(state: CachedAuthState): Promise<void> {
  await fs.mkdir(path.dirname(AUTH_STATE_PATH), { recursive: true });
  await fs.writeFile(AUTH_STATE_PATH, JSON.stringify(state), 'utf-8');
}

async function clearPersistedAuthState(): Promise<void> {
  await fs.rm(AUTH_STATE_PATH, { force: true });
}

async function bootstrapCookies(page: Page, cookies: AuthCookie[]): Promise<boolean> {
  await page.context().clearCookies();
  await page.context().addCookies(cookies);

  const valid = await validateBrowserSession(page);
  if (!valid) {
    await page.context().clearCookies();
  }
  return valid;
}

async function createFreshAuthState(page: Page): Promise<CachedAuthState> {
  const user = buildE2EUser();

  await page.context().clearCookies();
  await page.goto('/login', { waitUntil: 'domcontentloaded' });
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
    throw new Error(
      `Failed to login E2E user ${user.email}. `
      + 'Prepare fixed account first, e.g. run: '
      + '`cd apps/api && .venv/bin/python scripts/ensure_e2e_test_user.py`',
    );
  }

  const valid = await validateBrowserSession(page);
  if (!valid) {
    throw new Error(`Authenticated browser session could not be verified for ${user.email}.`);
  }

  return {
    user,
    cookies: await page.context().cookies(),
  };
}

async function getAuthState(page: Page, request: APIRequestContext): Promise<CachedAuthState> {
  void request;

  if (cachedAuthState && await bootstrapCookies(page, cachedAuthState.cookies)) {
    cachedAuthState.cookies = await page.context().cookies();
    return cachedAuthState;
  }

  if (!cachedAuthStatePromise) {
    cachedAuthStatePromise = (async () => {
      const persisted = await readPersistedAuthState();
      if (persisted && await bootstrapCookies(page, persisted.cookies)) {
        persisted.cookies = await page.context().cookies();
        await persistAuthState(persisted);
        return persisted;
      }

      await clearPersistedAuthState();
      const fresh = await createFreshAuthState(page);
      await persistAuthState(fresh);
      return fresh;
    })()
      .then((state) => {
        cachedAuthState = state;
        return state;
      })
      .catch((error) => {
        cachedAuthState = null;
        cachedAuthStatePromise = null;
        throw error;
      });
  }

  const state = await cachedAuthStatePromise;
  cachedAuthStatePromise = null;
  return state;
}

export async function registerAndLogin(page: Page, request: APIRequestContext): Promise<E2EUser> {
  const user = buildE2EUser();

  if (await validateBrowserSession(page)) {
    await page.goto('/dashboard', { waitUntil: 'domcontentloaded' });
    await page.waitForURL(/\/dashboard/, { timeout: 20000 });
    cachedAuthState = {
      user,
      cookies: await page.context().cookies(),
    };
    return user;
  }

  const authState = await getAuthState(page, request);
  await page.goto('/dashboard', { waitUntil: 'domcontentloaded' });
  await page.waitForURL(/\/dashboard/, { timeout: 20000 });
  authState.cookies = await page.context().cookies();
  await persistAuthState(authState);
  cachedAuthState = authState;
  return authState.user;
}
