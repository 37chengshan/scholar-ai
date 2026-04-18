import { expect, test } from '@playwright/test';
import { registerAndLogin } from './helpers/auth';

test.describe('Critical E2E - Knowledge Base', () => {
  test('create one knowledge base successfully', async ({ page, request }) => {
    await registerAndLogin(page, request);

    await page.waitForURL(/\/(dashboard|chat|knowledge-bases)/, { timeout: 20000 });

    await page.goto('/knowledge-bases');
    const createButton = page.getByRole('button', { name: '创建知识库' }).first();
    await expect(createButton).toBeVisible({ timeout: 15000 });

    await createButton.click();

    const kbName = `E2E-KB-${Date.now()}`;
    await page.fill('#kb-name', kbName);
    await page.fill('#kb-desc', 'Critical E2E knowledge base creation');

    await page.locator('div[role="dialog"] button:has-text("创建知识库")').click();

    const kbCard = page.locator('[data-kb-id]').filter({ hasText: kbName }).first();
    await expect(kbCard).toBeVisible({ timeout: 30000 });
  });
});
