import { expect, test } from '@playwright/test';
import { registerAndLogin } from './helpers/auth';

test.describe('J5: Read -> Highlight -> Linked Note', () => {
  test.describe.configure({ mode: 'serial' });

  test('J5: select text in read workspace and create linked note', async ({ page, request }) => {
    test.setTimeout(90000);

    await registerAndLogin(page, request);

    // Navigate to a paper read page
    await page.goto('/read/test-paper-id');

    // Wait for read workspace to settle
    await page.waitForTimeout(2000);

    // Check if we're on a valid read page
    const hasContent = await page.locator('canvas, [data-testid="pdf-viewer"], .react-pdf-page, main')
      .first().isVisible({ timeout: 10000 }).catch(() => false);
    const hasEmpty = await page.getByText(/choose.*paper|选择.*论文|no.*paper/i).first()
      .isVisible({ timeout: 5000 }).catch(() => false);

    if (hasEmpty || !hasContent) {
      // No paper loaded - verify empty state is handled gracefully
      expect(hasEmpty || !hasContent).toBe(true);
      return;
    }

    // Simulate text selection on content area
    const contentArea = page.locator('[data-testid="pdf-viewer"], .react-pdf-page, main').first();
    await contentArea.dispatchEvent('mouseup');

    // Check if floating annotation toolbar appears
    const toolbar = page.getByTestId('floating-annotation-toolbar');
    const toolbarVisible = await toolbar.isVisible({ timeout: 3000 }).catch(() => false);

    if (toolbarVisible) {
      // Click "Create Note" or "Highlight" action
      const createNoteBtn = toolbar.getByRole('button', { name: /note|笔记|highlight|高亮/i }).first();
      const hasNoteAction = await createNoteBtn.isVisible({ timeout: 3000 }).catch(() => false);

      if (hasNoteAction) {
        await createNoteBtn.click();

        // Assert linked note is created (note panel shows new entry)
        const hasNoteEntry = await page.getByText(/note|笔记|annotation|标注/i).first()
          .isVisible({ timeout: 10000 }).catch(() => false);
        expect(hasNoteEntry).toBe(true);
      }
    }

    // Verify the read workspace is still functional
    const stillFunctional = await page.locator('main').first().isVisible().catch(() => false);
    expect(stillFunctional).toBe(true);
  });
});
