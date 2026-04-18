import { expect, test } from '@playwright/test';
import { registerAndLogin } from './helpers/auth';

test.describe('Critical E2E - Chat', () => {
  test('login and complete one chat turn', async ({ page, request }) => {
    await registerAndLogin(page, request);

    await page.waitForURL(/\/(dashboard|chat|knowledge-bases)/, { timeout: 20000 });

    await page.goto('/chat');
    await expect(page.locator('textarea').first()).toBeVisible({ timeout: 10000 });

    const input = page.locator('textarea').first();
    await input.fill('请用一句话说明ScholarAI的用途');
    await input.press('Enter');

    await expect(input).toBeDisabled({ timeout: 15000 });
    await expect(input).toBeEnabled({ timeout: 120000 });
    await expect(page.locator('.magazine-body').first()).toBeVisible({ timeout: 30000 });
  });
});
