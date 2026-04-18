import { expect, test } from '@playwright/test';

const TEST_USER = {
  email: 'test@example.com',
  password: 'Test123!'
};

test.describe('Critical E2E - Retrieval', () => {
  test('chat answer contains retrieval/citation signal', async ({ page }) => {
    await page.goto('/login');

    await page.fill('input[type="email"]', TEST_USER.email);
    await page.fill('input[type="password"]', TEST_USER.password);
    await page.click('button[type="submit"]');

    await page.waitForURL(/\/(dashboard|chat|knowledge-bases)/, { timeout: 20000 });

    await page.goto('/chat');
    const input = page.locator('textarea').first();
    await expect(input).toBeVisible({ timeout: 10000 });

    await input.fill('请根据知识库内容给出一个带引用的回答');
    await input.press('Enter');

    await expect(input).toBeEnabled({ timeout: 120000 });

    const citationSignal = page.locator('[data-testid="citation"], .citation, text=/\[[0-9]+\]/');
    await expect(citationSignal.first()).toBeVisible({ timeout: 30000 });
  });
});
