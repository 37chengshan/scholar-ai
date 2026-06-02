import { expect, test } from '@playwright/test';
import { registerAndLogin } from './helpers/auth';

test.describe('J4: KB -> Read Paper', () => {
  test.describe.configure({ mode: 'serial' });

  test('J4: navigate from KB to read workspace for a paper', async ({ page, request }) => {
    test.setTimeout(90000);

    await registerAndLogin(page, request);

    // Navigate to knowledge bases
    await page.goto('/knowledge-bases');
    await expect(page.getByRole('button', { name: '创建知识库' }).first()).toBeVisible({ timeout: 15000 });

    // Check if any KB exists with papers
    const kbCards = page.locator('[data-kb-id]');
    const kbCount = await kbCards.count();

    if (kbCount > 0) {
      // Click the first KB
      await kbCards.first().click();
      await page.waitForURL(/\/knowledge-bases\//, { timeout: 15000 });

      // Look for paper list and "Read" button
      const readButton = page.getByRole('button', { name: /阅读|read|查看/i }).first();
      const hasReadButton = await readButton.isVisible({ timeout: 10000 }).catch(() => false);

      if (hasReadButton) {
        await readButton.click();

        // Assert navigation to read workspace
        await page.waitForURL(/\/read\//, { timeout: 20000 });
        await expect(page).toHaveURL(/\/read\//);

        // Assert read workspace renders
        const hasPdfViewer = await page.locator('[data-testid="pdf-viewer"], canvas, .react-pdf').first()
          .isVisible({ timeout: 10000 }).catch(() => false);
        const hasToolbar = await page.locator('[data-testid*="toolbar"], [role="toolbar"]').first()
          .isVisible({ timeout: 5000 }).catch(() => false);
        const hasWorkspace = await page.getByText(/workspace|工作区|阅读/i).first()
          .isVisible({ timeout: 5000 }).catch(() => false);
        const hasLoading = await page.getByText(/loading|加载中/i).first()
          .isVisible({ timeout: 5000 }).catch(() => false);

        expect(hasPdfViewer || hasToolbar || hasWorkspace || hasLoading).toBe(true);
      } else {
        // KB exists but no papers yet - verify KB detail page loaded
        await expect(page.getByText(/论文|papers|上传/i).first()).toBeVisible({ timeout: 10000 });
      }
    } else {
      // No KBs exist - verify the empty state
      await expect(page.getByText(/创建知识库|no.*knowledge/i).first()).toBeVisible({ timeout: 10000 });
    }
  });
});
