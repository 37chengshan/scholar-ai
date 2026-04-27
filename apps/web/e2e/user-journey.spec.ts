import { expect, test, type Page } from '@playwright/test';
import { registerAndLogin } from './helpers/auth';

const PUBLIC_ROUTES = ['/', '/login', '/register', '/forgot-password', '/reset-password'];
const PROTECTED_ROUTES = [
  '/dashboard',
  '/knowledge-bases',
  '/search',
  '/read/e2e-placeholder-paper',
  '/chat',
  '/settings',
  '/notes',
];

async function assertAppShellVisible(page: Page): Promise<void> {
  await expect(page.locator('#root')).toBeVisible({ timeout: 15000 });
}

test.describe('E2E 用户全页面交互回归', () => {
  test.describe.configure({ mode: 'serial' });

  test('公开页面可访问且渲染稳定', async ({ page }) => {
    for (const route of PUBLIC_ROUTES) {
      await page.goto(route);
      await assertAppShellVisible(page);
    }
  });

  test('登录后覆盖所有受保护页面并执行关键交互', async ({ page, request }) => {
    await registerAndLogin(page, request);
    await page.waitForURL(/\/dashboard/, { timeout: 20000 });

    for (const route of PROTECTED_ROUTES) {
      await page.goto(route);
      await expect(page).not.toHaveURL(/\/login/);
      await assertAppShellVisible(page);
    }

    await test.step('知识库页: 打开并关闭创建弹窗', async () => {
      await page.goto('/knowledge-bases');
      const createButton = page.getByRole('button', { name: /创建知识库/i }).first();
      await expect(createButton).toBeVisible({ timeout: 15000 });
      await createButton.click();
      await expect(page.locator('div[role="dialog"]').first()).toBeVisible({ timeout: 10000 });
      await page.keyboard.press('Escape');
    });

    await test.step('检索页: 输入查询并触发检索', async () => {
      await page.goto('/search');
      const queryInput = page.getByTestId('search-query-input').first();
      const queryButton = page.getByTestId('search-query-button').first();
      await expect(queryInput).toBeVisible({ timeout: 15000 });
      await queryInput.fill('transformer retrieval');
      await queryButton.click();
      await expect(page.getByTestId('search-results-panel')).toBeVisible({ timeout: 30000 });
    });

    await test.step('Chat 页: 发起一轮消息并等待流式结束', async () => {
      await page.goto('/chat');
      const input = page.locator('textarea').first();
      await expect(input).toBeVisible({ timeout: 10000 });
      await input.fill('请简要介绍 ScholarAI 的核心能力。');
      await input.press('Enter');
      await expect(input).toBeEnabled({ timeout: 120000 });
      await expect(page.getByText(/ScholarAI/).first()).toBeVisible({ timeout: 30000 });
    });

    await test.step('设置页: 切换配置分区', async () => {
      await page.goto('/settings');
      await expect(page.getByText(/System|系统/).first()).toBeVisible({ timeout: 15000 });
      await page.getByRole('button', { name: /Security|安全设置/i }).first().click();
      await expect(page.getByText(/Authentication|身份验证/).first()).toBeVisible({ timeout: 15000 });
    });

    await test.step('笔记页: 创建新笔记入口可用', async () => {
      await page.goto('/notes');
      const createNoteButton = page.getByRole('button', { name: /新建|新建笔记/i }).first();
      await expect(createNoteButton).toBeVisible({ timeout: 15000 });
      await createNoteButton.click();
      await expect(page.getByText(/未命名笔记/).first()).toBeVisible({ timeout: 15000 });
    });
  });
});
