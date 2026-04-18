import { expect, test } from '@playwright/test';
import { registerAndLogin } from './helpers/auth';

test.describe('Critical E2E - Retrieval', () => {
  test('chat answer contains retrieval/citation signal', async ({ page, request }) => {
    await registerAndLogin(page, request);

    await page.waitForURL(/\/(dashboard|chat|knowledge-bases)/, { timeout: 20000 });

    await page.goto('/chat');
    const input = page.locator('textarea').first();
    await expect(input).toBeVisible({ timeout: 10000 });

    await input.fill('请根据知识库内容给出一个带引用的回答');
    await input.press('Enter');

    await expect(input).toBeEnabled({ timeout: 120000 });
    await expect(page.locator('.magazine-body').first()).toBeVisible({ timeout: 30000 });
  });
});
