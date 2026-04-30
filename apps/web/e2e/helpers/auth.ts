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

let cachedAuthStatePromise: Promise<CachedAuthState> | null = null;
let cachedAuthState: CachedAuthState | null = null;

const AUTH_STATE_PATH = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../.auth/e2e-auth-state.json');

function buildE2EUser(): E2EUser {
  return {
    email: process.env.E2E_USER_EMAIL ?? process.env.PR19_E2E_USER_EMAIL ?? 'pr19-e2e@example.com',
    password: process.env.E2E_USER_PASSWORD ?? process.env.PR19_E2E_USER_PASSWORD ?? 'Pr19E2EPass123',
    name: process.env.E2E_USER_NAME ?? 'PR19 E2E User',
  };
}

async function createAuthState(page: Page, request: APIRequestContext): Promise<CachedAuthState> {
  void request;
  const user = buildE2EUser();

  await page.goto('/login');
  await page.waitForLoadState('domcontentloaded');

  // A fresh page can still inherit valid cookies from an earlier attempt.
  // If /login immediately redirects to /dashboard, reuse that authenticated state.
  if (/\/dashboard(?:[/?#]|$)/.test(page.url())) {
    await page.locator('#root').waitFor({ timeout: 20000 });
    return {
      user,
      cookies: await page.context().cookies(),
    };
  }

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
    await page.waitForURL(/\/dashboard/, { timeout: 20000 });
  } catch {
    throw new Error(
      `Failed to login E2E user ${user.email}. `
      + 'Prepare fixed account first, e.g. run: '
      + '`cd apps/api && .venv/bin/python scripts/ensure_e2e_test_user.py`',
    );
  }

  await page.locator('#root').waitFor({ timeout: 20000 });

  return {
    user,
    cookies: await page.context().cookies(),
  };
}

async function readPersistedAuthState(): Promise<CachedAuthState | null> {
  try {
    const content = await fs.readFile(AUTH_STATE_PATH, 'utf-8');
    const parsed = JSON.parse(content) as CachedAuthState;
    if (!parsed?.user?.email || !Array.isArray(parsed?.cookies)) {
      return null;
    }
    const hasWarmHintCookie = parsed.cookies.some((cookie) => cookie.name === 'authHint' && cookie.value === '1');
    if (!hasWarmHintCookie) {
      return null;
    }
    return parsed;
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

async function getAuthState(page: Page, request: APIRequestContext): Promise<CachedAuthState> {
  if (cachedAuthState) {
    return cachedAuthState;
  }

  if (!cachedAuthStatePromise) {
    cachedAuthStatePromise = (async () => {
      const persisted = await readPersistedAuthState();
      if (persisted) {
        return persisted;
      }

      const fresh = await createAuthState(page, request);
      await persistAuthState(fresh);
      return fresh;
    })()
      .then((state) => {
        cachedAuthState = state;
        return state;
      })
      .catch((error) => {
        cachedAuthStatePromise = null;
        cachedAuthState = null;
        throw error;
      });
  }

  return cachedAuthStatePromise;
}

export async function registerAndLogin(page: Page, request: APIRequestContext): Promise<E2EUser> {
  let authState = await getAuthState(page, request);

  // Reuse the authenticated browser cookies after the first login in this worker.
  await page.context().addCookies(authState.cookies);
  await page.goto('/dashboard');
  try {
    await page.waitForURL(/\/dashboard/, { timeout: 20000 });
  } catch {
    // Persisted cookies might have expired; refresh once via UI login.
    cachedAuthState = null;
    cachedAuthStatePromise = null;
    await clearPersistedAuthState();
    await page.context().clearCookies();

    authState = await createAuthState(page, request);
    await persistAuthState(authState);
    await page.context().addCookies(authState.cookies);
    await page.goto('/dashboard');
    await page.waitForURL(/\/dashboard/, { timeout: 20000 });
  }

  return authState.user;
}
