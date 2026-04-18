import { expect, test } from '@playwright/test';

test.describe('Critical E2E - Chat Session Search', () => {
  test('filters sessions from sidebar search input', async ({ page }) => {
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

    await page.route('**/api/v1/sessions?**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          sessions: [
            {
              id: 'session-alpha',
              title: 'Alpha Research Notes',
              status: 'active',
              messageCount: 3,
              createdAt: '2026-01-01T00:00:00Z',
              updatedAt: '2026-01-02T00:00:00Z',
            },
            {
              id: 'session-beta',
              title: 'Beta Experiment Log',
              status: 'active',
              messageCount: 1,
              createdAt: '2026-01-03T00:00:00Z',
              updatedAt: '2026-01-04T00:00:00Z',
            },
          ],
          total: 2,
          limit: 50,
        }),
      });
    });

    await page.route('**/api/v1/sessions/*/messages**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          messages: [],
        }),
      });
    });

    await page.goto('/chat');

    const searchInput = page.getByTestId('session-search-input');
    await expect(searchInput).toBeVisible({ timeout: 10000 });

    await expect(page.getByTestId('session-item')).toHaveCount(2, { timeout: 10000 });

    await searchInput.fill('Alpha');
    await expect(page.getByTestId('session-item')).toHaveCount(1, { timeout: 10000 });
    await expect(page.getByTestId('session-item').first()).toContainText('Alpha Research Notes');

    await page.getByTestId('session-item').first().click();
    await expect(page.getByRole('heading', { name: 'Alpha Research Notes' })).toBeVisible({ timeout: 10000 });

    await searchInput.fill('No-Match-Query');
    await expect(page.getByTestId('session-empty-state')).toBeVisible({ timeout: 10000 });
  });
});
