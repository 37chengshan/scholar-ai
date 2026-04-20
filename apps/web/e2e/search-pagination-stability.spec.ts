import { expect, test } from '@playwright/test';

function extractTitleIndex(text: string): number {
  const match = text.match(/agent-title-(\d+)/);
  return match ? Number(match[1]) : -1;
}

test.describe('Critical E2E - Search Pagination Stability', () => {
  test('keeps result panel visible during page transitions', async ({ page }) => {
    await page.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'e2e-user-1',
          email: 'e2e@example.com',
          name: 'E2E User',
          roles: ['user'],
          email_verified: true,
        }),
      });
    });

    await page.route('**/api/v1/search/unified**', async (route) => {
      const requestUrl = new URL(route.request().url());
      const query = requestUrl.searchParams.get('query') || 'agent';
      const limit = Number(requestUrl.searchParams.get('limit') || '20');
      const offset = Number(requestUrl.searchParams.get('offset') || '0');

      if (offset > 0) {
        await new Promise((resolve) => setTimeout(resolve, 250));
      }

      const results = Array.from({ length: limit }, (_, index) => ({
        id: `${query}-${offset + index}`,
        title: `${query}-title-${offset + index}`,
        authors: ['E2E Author'],
        source: 'arxiv',
        year: 2025,
      }));

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          query,
          results,
          total: 60,
          filters: {
            year_from: null,
            year_to: null,
          },
        }),
      });
    });

    await page.goto('/search');

    const queryInput = page.getByTestId('search-query-input');
    await expect(queryInput).toBeVisible({ timeout: 10000 });
    await queryInput.fill('agent');

    const firstCard = page.getByTestId('search-result-card').first();
    await expect(firstCard).toBeVisible({ timeout: 10000 });
    const firstCardBefore = await firstCard.textContent();
    const beforeIndex = extractTitleIndex(firstCardBefore || '');
    expect(beforeIndex).toBeGreaterThanOrEqual(0);

    const nextButton = page.getByTestId('search-pagination-next');
    await expect(nextButton).toBeVisible({ timeout: 10000 });
    await nextButton.click();

    await expect(page.getByTestId('search-results-panel')).toBeVisible();
    await expect
      .poll(async () => {
        const current = await firstCard.textContent();
        return extractTitleIndex(current || '');
      }, { timeout: 10000 })
      .toBe(beforeIndex + 20);

    const prevButton = page.getByTestId('search-pagination-prev');
    await prevButton.click();

    await expect
      .poll(async () => {
        const current = await firstCard.textContent();
        return extractTitleIndex(current || '');
      }, { timeout: 10000 })
      .toBe(beforeIndex);
  });
});
