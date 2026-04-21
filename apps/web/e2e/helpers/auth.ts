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

  return {
    user,
    cookies: await page.context().cookies(),
  };
}

async function getAuthState(page: Page, request: APIRequestContext): Promise<CachedAuthState> {
  if (cachedAuthState) {
    return cachedAuthState;
  }

  if (!cachedAuthStatePromise) {
    cachedAuthStatePromise = createAuthState(page, request)
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
  const authState = await getAuthState(page, request);

  // Reuse the authenticated browser cookies after the first login in this worker.
  await page.context().addCookies(authState.cookies);
  await page.goto('/chat');
  await page.waitForURL(/\/(dashboard|chat|knowledge-bases)/, { timeout: 20000 });

  return authState.user;
}
