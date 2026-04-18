import { expect, test } from '@playwright/test';
import { registerAndLogin } from './helpers/auth';

test.describe('Critical E2E - Retrieval', () => {
  test('chat answer contains retrieval/citation signal', async ({ page, request }) => {
    const messageId = `e2e-retrieval-${Date.now()}`;
    const citedAnswer = '根据知识库证据，该结论是成立的[1]。';
    const citationTitle = 'E2E Retrieval Evidence';

    await page.route('**/api/v1/chat/stream', async (route) => {
      const sseBody = [
        'event: session_start',
        `data: {"message_id":"${messageId}","session_id":"e2e-session","task_type":"kb_qa"}`,
        '',
        'event: message',
        `data: {"message_id":"${messageId}","delta":"${citedAnswer}"}`,
        '',
        'event: citation',
        `data: {"message_id":"${messageId}","paper_id":"paper-e2e-1","title":"${citationTitle}","authors":["E2E Author"],"year":2026,"snippet":"retrieval snippet","score":0.92,"content_type":"text"}`,
        '',
        'event: done',
        `data: {"message_id":"${messageId}","tokens_used":21,"cost":0}`,
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
    const input = page.locator('textarea').first();
    await expect(input).toBeVisible({ timeout: 10000 });

    await input.fill('请根据知识库内容给出一个带引用的回答');
    await input.press('Enter');

    await expect(input).toBeEnabled({ timeout: 120000 });

    const citationSignal = page.locator('.mag-citation, [data-testid="citation"], .citation');
    await expect(citationSignal.first()).toBeVisible({ timeout: 30000 });
    await expect(page.getByText(citationTitle)).toBeVisible({ timeout: 30000 });
  });
});
