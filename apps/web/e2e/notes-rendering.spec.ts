import { expect, test } from '@playwright/test';
import { registerAndLogin } from './helpers/auth';

test('notes page never renders raw tiptap json', async ({ page, request }) => {
  await registerAndLogin(page, request);
  await page.goto('/notes');

  await expect(page.locator('#root')).toBeVisible({ timeout: 15000 });
  await expect(page.locator('body')).not.toContainText('{"type":"doc"');
  await expect(page.locator('body')).not.toContainText('"content":[{"type":"paragraph"');
});