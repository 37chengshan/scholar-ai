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
  await page.goto('/chat');

  const input = page.getByTestId('chat-composer').locator('textarea');
  await expect(input).toBeVisible({ timeout: 10000 });
  await input.fill('你好');
  await input.press('Enter');
  await expect(input).toBeEnabled({ timeout: 120000 });

  const messageList = page.getByTestId('chat-message-list');
  await expect(messageList).toBeVisible({ timeout: 30000 });

  for (const viewport of viewports) {
    await page.setViewportSize(viewport);
    await page.goto('/chat');

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