import { expect, test } from '@playwright/test';
import { registerAndLogin } from './helpers/auth';

test.describe('Critical E2E - Retrieval', () => {
  test('chat answer contains retrieval/citation signal', async ({ page, request }) => {
    await registerAndLogin(page, request);

    await page.route('**/api/v1/sessions?**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: { sessions: [], total: 0, limit: 50 } }),
      });
    });

    await page.route('**/api/v1/sessions', async (route) => {
      if (route.request().method() !== 'POST') {
        await route.fallback();
        return;
      }

      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            id: 'retrieval-e2e-session',
            title: 'Retrieval E2E Session',
            status: 'active',
            messageCount: 0,
            createdAt: '2026-05-08T00:00:00Z',
            updatedAt: '2026-05-08T00:00:00Z',
            metadata: {},
          },
        }),
      });
    });

    await page.route('**/api/v1/chat/stream', async (route) => {
      const mockSse = [
        'event: session_start',
        'data: {"session_id":"retrieval-e2e-session","task_type":"kb_qa","message_id":"msg-e2e-1"}',
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

    await page.goto('/chat?new=1');
    await expect(page).toHaveURL(/\/chat$/);
    const input = page.locator('textarea').first();
    await expect(input).toBeVisible({ timeout: 10000 });

    await input.fill('请根据知识库内容给出一个带引用的回答');
    await input.press('Enter');

    await expect(page.getByTestId('chat-message-list')).toBeVisible({ timeout: 30000 });
    await expect(page.getByText('这是一个带引用信号的回答。')).toBeVisible({ timeout: 30000 });
  });
});
