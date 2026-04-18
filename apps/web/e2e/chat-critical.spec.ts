import { expect, test } from '@playwright/test';
import { registerAndLogin } from './helpers/auth';

test.describe('Critical E2E - Chat', () => {
  test('login and complete one chat turn', async ({ page, request }) => {
    const messageId = `e2e-chat-${Date.now()}`;
    const mockedAnswer = 'ScholarAI 是一个用于学术检索与问答的助手。';

    await page.route('**/api/v1/chat/stream', async (route) => {
      const sseBody = [
        'event: session_start',
        `data: {"message_id":"${messageId}","session_id":"e2e-session","task_type":"general"}`,
        '',
        'event: message',
        `data: {"message_id":"${messageId}","delta":"${mockedAnswer}"}`,
        '',
        'event: done',
        `data: {"message_id":"${messageId}","tokens_used":12,"cost":0}`,
        '',
      ].join('\n');

      await route.fulfill({
        status: 200,
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
          Connection: 'keep-alive',
        },
        body: sseBody,
      });
    });

    await registerAndLogin(page, request);

    await page.waitForURL(/\/(dashboard|chat|knowledge-bases)/, { timeout: 20000 });

    await page.goto('/chat');
    await expect(page.locator('textarea').first()).toBeVisible({ timeout: 10000 });

    const input = page.locator('textarea').first();
    await input.fill('请用一句话说明ScholarAI的用途');
    await input.press('Enter');

    await expect(input).toBeDisabled({ timeout: 15000 });
    await expect(input).toBeEnabled({ timeout: 120000 });

    await expect(page.getByText(mockedAnswer)).toBeVisible({ timeout: 30000 });
  });
});
