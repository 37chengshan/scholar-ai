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

    const createResponsePromise = page.waitForResponse((res) => (
      res.url().includes('/api/v1/knowledge-bases')
      && res.request().method() === 'POST'
    ));
    await page.locator('div[role="dialog"] button:has-text("创建知识库")').click();

    const createResponse = await createResponsePromise;
    expect(createResponse.status()).toBe(201);
    const payload = await createResponse.json();
    const createdKbId = payload?.data?.id;
    expect(createdKbId).toBeTruthy();

    const createdCard = page.locator(`[data-kb-id="${createdKbId}"]`).first();
    await expect(createdCard).toBeVisible({ timeout: 30000 });
    await createdCard.click();
    await expect(page).toHaveURL(new RegExp(`/knowledge-bases/${createdKbId}`), { timeout: 15000 });
  });
});
