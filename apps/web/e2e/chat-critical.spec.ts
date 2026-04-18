import { expect, test } from '@playwright/test';

const TEST_USER = {
  email: 'test@example.com',
  password: 'Test123!'
};

test.describe('Critical E2E - Chat', () => {
  test('login and complete one chat turn', async ({ page }) => {
    await page.goto('/login');

    await page.fill('input[type="email"]', TEST_USER.email);
    await page.fill('input[type="password"]', TEST_USER.password);
    await page.click('button[type="submit"]');

    await page.waitForURL(/\/(dashboard|chat|knowledge-bases)/, { timeout: 20000 });

    await page.goto('/chat');
    await expect(page.locator('textarea').first()).toBeVisible({ timeout: 10000 });

    const input = page.locator('textarea').first();
    await input.fill('请用一句话说明ScholarAI的用途');
    await input.press('Enter');

    await expect(input).toBeDisabled({ timeout: 15000 });
    await expect(input).toBeEnabled({ timeout: 120000 });

    const messageCount = await page.locator('[data-testid="ai-response"], .message, .response').count();
    expect(messageCount).toBeGreaterThan(0);
  });
});
