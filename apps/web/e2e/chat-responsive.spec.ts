import { expect, test } from '@playwright/test';
import { registerAndLogin } from './helpers/auth';

const viewports = [
  { width: 1440, height: 900 },
  { width: 1200, height: 800 },
  { width: 900, height: 800 },
  { width: 760, height: 800 },
];

test('chat layout works across core breakpoints without overflow', async ({ page, request }) => {
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
          id: 'responsive-e2e-session',
          title: 'Responsive E2E Session',
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
      'data: {"session_id":"responsive-e2e-session","task_type":"general","message_id":"msg-responsive-1"}',
      '',
      'event: message',
      'data: {"delta":"响应式布局测试回答。","seq":1,"message_id":"msg-responsive-1"}',
      '',
      'event: done',
      'data: {"finish_reason":"stop","tokens_used":8,"message_id":"msg-responsive-1"}',
      '',
    ].join('\n');

    await route.fulfill({
      status: 200,
      contentType: 'text/event-stream',
      body: mockSse,
    });
  });

  await page.goto('/chat?new=1');
  await expect(page).toHaveURL(/\/chat$/);

  const input = page.getByTestId('chat-composer').locator('textarea');
  await expect(input).toBeVisible({ timeout: 10000 });
  await input.fill('你好');
  await input.press('Enter');

  const messageList = page.getByTestId('chat-message-list');
  await expect(messageList).toBeVisible({ timeout: 30000 });
  await expect(page.getByText('你好').first()).toBeVisible({ timeout: 30000 });

  for (const viewport of viewports) {
    await page.setViewportSize(viewport);
    await expect(page.getByText('你好').first()).toBeVisible({ timeout: 10000 });

    const composer = page.getByTestId('chat-composer');
    await expect(page.getByTestId('chat-composer').locator('textarea')).toBeVisible({ timeout: 10000 });
    await expect(composer).toBeVisible();
    await expect(messageList).toBeVisible({ timeout: 30000 });

    const layoutCheck = await page.evaluate(() => {
      const composerEl = document.querySelector('[data-testid="chat-composer"]') as HTMLElement | null;
      const messageListEl = document.querySelector('[data-testid="chat-message-list"]') as HTMLElement | null;
      const bodyOverflow = document.body.scrollWidth > document.body.clientWidth;

      if (!composerEl || !messageListEl) {
        return {
          ok: false,
          bodyOverflow,
          composerWithinViewport: false,
          messageListWithinViewport: false,
        };
      }

      const vw = window.innerWidth;
      const composerRect = composerEl.getBoundingClientRect();
      const messageRect = messageListEl.getBoundingClientRect();

      const composerWithinViewport = composerRect.left >= -1 && composerRect.right <= vw + 1;
      const messageListWithinViewport = messageRect.left >= -1 && messageRect.right <= vw + 1;

      return {
        ok: !bodyOverflow && composerWithinViewport && messageListWithinViewport,
        bodyOverflow,
        composerWithinViewport,
        messageListWithinViewport,
      };
    });

    expect(layoutCheck.bodyOverflow).toBe(false);
    expect(layoutCheck.composerWithinViewport).toBe(true);
    expect(layoutCheck.messageListWithinViewport).toBe(true);
    expect(layoutCheck.ok).toBe(true);
  }
});
