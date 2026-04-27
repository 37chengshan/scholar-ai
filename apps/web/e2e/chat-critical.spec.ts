import { expect, test } from '@playwright/test';
import { registerAndLogin } from './helpers/auth';

test.describe('Critical E2E - Chat', () => {
  test.describe.configure({ mode: 'serial' });

  test('login redirects to dashboard and chat nav works', async ({ page, request }) => {
    await registerAndLogin(page, request);

    await page.waitForURL(/\/dashboard/, { timeout: 20000 });
    await expect(page).toHaveURL(/\/dashboard/);

    await page.getByRole('link', { name: /对话|Chat/i }).click();
    await expect(page).toHaveURL(/\/chat/);
    const input = page.getByTestId('chat-composer').locator('textarea');
    await expect(input).toBeVisible({ timeout: 10000 });
  });

  test('chat stream request carries session and mode', async ({ page, request }) => {
    await registerAndLogin(page, request);
    await page.goto('/chat');
    const input = page.getByTestId('chat-composer').locator('textarea');
    await expect(input).toBeVisible({ timeout: 10000 });

    const streamRequest = page.waitForRequest((req) => (
      req.url().includes('/api/v1/chat/stream') && req.method() === 'POST'
    ));

    await input.fill('请用一句话说明ScholarAI的用途');
    await input.press('Enter');

    const req = await streamRequest;
    const body = req.postDataJSON();

    expect(body.message).toContain('ScholarAI');
    expect(body.session_id).toBeTruthy();
    expect(body.mode).toBeTruthy();
  });

  test('new chat sends first message and binds session URL', async ({ page, request }) => {
    await registerAndLogin(page, request);

    await page.goto('/chat?new=1');
    const input = page.getByTestId('chat-composer').locator('textarea');
    await expect(input).toBeVisible({ timeout: 10000 });
    await expect(page).toHaveURL(/\/chat$/);

    const createSessionResponsePromise = page.waitForResponse((res) => (
      res.url().includes('/api/v1/sessions')
      && res.request().method() === 'POST'
    ));
    const streamRequestPromise = page.waitForRequest((req) => (
      req.url().includes('/api/v1/chat/stream')
      && req.method() === 'POST'
    ));

    await input.fill('请解释RAG是什么');
    await expect(page.getByRole('button', { name: /发送消息|send message/i })).toBeEnabled({ timeout: 10000 });
    await input.press('Enter');

    const createSessionResponse = await createSessionResponsePromise;
    const createSessionPayload = await createSessionResponse.json();
    const createdSessionId = createSessionPayload?.data?.id || createSessionPayload?.id;

    expect(createdSessionId).toBeTruthy();

    const streamRequest = await streamRequestPromise;
    const streamBody = streamRequest.postDataJSON();
    expect(streamBody.session_id).toBe(createdSessionId);

    await expect(page).toHaveURL(/\/chat\?session=/, { timeout: 20000 });
    await expect(page).toHaveURL(new RegExp(`/chat\\?session=${createdSessionId}`), { timeout: 20000 });
    await expect(input).toBeEnabled({ timeout: 120000 });
  });
});
