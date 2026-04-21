import type { APIRequestContext, Page } from '@playwright/test';

type E2EUser = {
  email: string;
  password: string;
  name: string;
};

function buildE2EUser(): E2EUser {
  const nonce = `${Date.now()}-${Math.floor(Math.random() * 100000)}`;
  return {
    email: `e2e-${nonce}@example.com`,
    password: 'Test1234A',
    name: `E2E User ${nonce.slice(-6)}`,
  };
}

export async function registerAndLogin(page: Page, request: APIRequestContext): Promise<E2EUser> {
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

  // Wait for the authenticated workspace to fully mount before returning.
  // Some specs immediately trigger a hard navigation after login, and this
  // extra guard avoids racing the auth/session bootstrap.
  await page.waitForURL(/\/chat/, { timeout: 20000 });
  await page.getByTestId('chat-workspace-root').waitFor({ timeout: 20000 });

  return user;
}
