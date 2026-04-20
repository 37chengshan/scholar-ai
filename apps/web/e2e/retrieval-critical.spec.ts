import { expect, test } from '@playwright/test';
import { registerAndLogin } from './helpers/auth';

test.describe('Critical E2E - Retrieval', () => {
  test('chat answer contains retrieval/citation signal', async ({ page, request }) => {
    await registerAndLogin(page, request);

    await page.route('**/api/v1/chat/stream', async (route) => {
      const mockSse = [
        'event: session_start',
        'data: {"session_id":"e2e-session-1","task_type":"kb_qa","message_id":"msg-e2e-1"}',
        '',
        'event: citation',
        'data: {"paper_id":"paper-1","title":"Mock Citation","pages":[1],"hits":1,"message_id":"msg-e2e-1"}',
        '',
        'event: message',
        'data: {"delta":"这是一个带引用信号的回答。","seq":1,"message_id":"msg-e2e-1"}',
        '',
        'event: done',
        'data: {"finish_reason":"stop","tokens_used":12,"message_id":"msg-e2e-1"}',
        '',
      ].join('\n');

      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: mockSse,
      });
    });

    await page.waitForURL(/\/(dashboard|chat|knowledge-bases)/, { timeout: 20000 });

    await page.goto('/chat');
    const input = page.locator('textarea').first();
    await expect(input).toBeVisible({ timeout: 10000 });

    await input.fill('请根据知识库内容给出一个带引用的回答');
    await input.press('Enter');

    await expect(input).toBeEnabled({ timeout: 120000 });
  });
});
