import { expect, test } from '@playwright/test';
import { registerAndLogin } from './helpers/auth';

test('general greeting does not show evidence panel', async ({ page, request }) => {
  await registerAndLogin(page, request);
  await page.goto('/chat?new=1');

  const input = page.locator('textarea').first();
  await input.fill('你好');
  await input.press('Enter');

  await expect(input).toBeEnabled({ timeout: 120000 });
  await expect(page.getByText(/coverage/i)).toHaveCount(0);
  await expect(page.getByText(/ABSTAIN/i)).toHaveCount(0);
});