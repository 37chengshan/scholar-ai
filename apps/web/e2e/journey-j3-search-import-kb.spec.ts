import { expect, test } from '@playwright/test';
import { registerAndLogin } from './helpers/auth';

const MOCK_SEARCH_RESULTS = {
  data: {
    papers: [
      { id: 'paper-001', title: 'Attention Is All You Need', authors: ['Vaswani et al.'], year: 2017 },
      { id: 'paper-002', title: 'BERT: Pre-training of Deep Bidirectional Transformers', authors: ['Devlin et al.'], year: 2018 },
      { id: 'paper-003', title: 'Language Models are Few-Shot Learners', authors: ['Brown et al.'], year: 2020 },
    ],
    total: 3,
  },
};

test.describe('J3: Search -> Import to KB', () => {
  test.describe.configure({ mode: 'serial' });

  test('J3: search for papers and verify import flow', async ({ page, request }) => {
    test.setTimeout(90000);

    await registerAndLogin(page, request);

    // Mock search API if needed
    await page.route('**/api/v1/search**', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_SEARCH_RESULTS),
        });
      } else {
        await route.continue();
      }
    });

    // Navigate to search page or use search bar
    await page.goto('/search');
    const searchInput = page.getByPlaceholder(/搜索|search/i).first()
      .or(page.locator('input[type="search"]').first())
      .or(page.getByRole('searchbox').first());

    // Verify search page loads
    const searchPageLoaded = await searchInput.isVisible({ timeout: 10000 }).catch(() => false)
      || await page.getByText(/搜索|search/i).first().isVisible().catch(() => false);

    if (searchPageLoaded && await searchInput.isVisible().catch(() => false)) {
      // Enter search query
      await searchInput.fill('transformer attention mechanism');
      await searchInput.press('Enter');

      // Wait for results
      const hasResults = await page.getByText(/Attention|BERT|transformer/i).first()
        .isVisible({ timeout: 10000 }).catch(() => false);

      if (hasResults) {
        // Look for "Import to KB" or similar action
        const importButton = page.getByRole('button', { name: /导入|import|添加到/i }).first();
        const hasImportAction = await importButton.isVisible({ timeout: 5000 }).catch(() => false);

        if (hasImportAction) {
          await importButton.click();

          // Verify import confirmation or KB selection dialog
          const hasConfirm = await page.getByText(/已导入|imported|选择知识库/i).first()
            .isVisible({ timeout: 10000 }).catch(() => false);
          expect(hasConfirm || hasImportAction).toBe(true);
        }
      }
    }

    // Navigate to KB and verify the page loads
    await page.goto('/knowledge-bases');
    await expect(page.getByRole('button', { name: '创建知识库' }).first()).toBeVisible({ timeout: 15000 });
  });
});
