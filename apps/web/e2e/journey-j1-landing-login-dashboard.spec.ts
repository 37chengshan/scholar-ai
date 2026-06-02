import { expect, test } from '@playwright/test';
import { registerAndLogin } from './helpers/auth';

test.describe('J1: Landing -> Login -> Dashboard', () => {
  test.describe.configure({ mode: 'serial' });

  test('J1: landing page renders and login redirects to dashboard', async ({ page, request }) => {
    // Step 1: Navigate to landing page
    await page.goto('/', { waitUntil: 'domcontentloaded' });

    // Step 2: Assert landing page renders (heading or CTA visible)
    const hasHeading = await page.getByRole('heading').first().isVisible().catch(() => false);
    const hasCta = await page.getByRole('link', { name: /get started|开始|登录|login/i }).first().isVisible().catch(() => false);
    const hasContent = await page.locator('main, [role="main"], section').first().isVisible().catch(() => false);
    expect(hasHeading || hasCta || hasContent).toBe(true);

    // Step 3: Login via helper
    await registerAndLogin(page, request);

    // Step 4: Assert redirect to dashboard
    await page.waitForURL(/\/dashboard/, { timeout: 20000 });
    await expect(page).toHaveURL(/\/dashboard/);

    // Step 5: Assert dashboard renders meaningful content
    const dashboardReady = await page.getByRole('heading').first().isVisible().catch(() => false)
      || await page.locator('[data-testid]').first().isVisible().catch(() => false)
      || await page.getByRole('navigation').first().isVisible().catch(() => false);
    expect(dashboardReady).toBe(true);
  });
});
