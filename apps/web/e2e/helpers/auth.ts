import type { APIRequestContext, BrowserContext, Page } from '@playwright/test';

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

function buildE2EUser(): E2EUser {
  const nonce = `${Date.now()}-${Math.floor(Math.random() * 100000)}`;
  return {
    email: `e2e-${nonce}@example.com`,
    password: 'Test1234A',
    name: `E2E User ${nonce.slice(-6)}`,
  };
}

async function createAuthState(page: Page, request: APIRequestContext): Promise<CachedAuthState> {
  const user = buildE2EUser();

  const registerResponse = await request.post('/api/v1/auth/register', {
    data: {
      email: user.email,
      password: user.password,
      name: user.name,
    },
  });

  if (!registerResponse.ok()) {
    const body = await registerResponse.text();
    throw new Error(`Failed to register E2E user: ${registerResponse.status()} ${body}`);
  }

  await page.goto('/login');
  await page.fill('input[type="email"]', user.email);
  await page.fill('input[type="password"]', user.password);
  await page.click('button[type="submit"]');
  await page.waitForURL(/\/chat/, { timeout: 20000 });
  await page.getByTestId('chat-workspace-root').waitFor({ timeout: 20000 });

  // Wait for the authenticated workspace to fully mount before returning.
  // Some specs immediately trigger a hard navigation after login, and this
  // extra guard avoids racing the auth/session bootstrap.
  await page.waitForURL(/\/chat/, { timeout: 20000 });
  await page.getByTestId('chat-workspace-root').waitFor({ timeout: 20000 });

  return user;
}
