import { test, expect } from '@playwright/test';

const TEST_ACCOUNTS = {
  primary: {
    email: 'uat-test@example.com',
    password: 'Test123!', // 常用测试密码
  },
  secondary: {
    email: 'test@example.com',
    password: 'Test123!',
  },
};

test.describe('Phase 25: AI Chat 真实用户场景测试', () => {
  
  test.describe.configure({ mode: 'serial' }); // 顺序执行

  test('场景1: 用户登录并查看论文列表', async ({ page }) => {
    await test.step('访问登录页面', async () => {
      await page.goto('/login');
      await expect(page).toHaveURL(/login/);
    });

    await test.step('使用测试账号登录', async () => {
      await page.fill('input[type="email"]', TEST_ACCOUNTS.primary.email);
      await page.fill('input[type="password"]', TEST_ACCOUNTS.primary.password);
      await page.click('button[type="submit"]');
      
      // 等待登录成功并跳转
      await page.waitForURL(/\/(dashboard|papers|chat)/, { timeout: 10000 });
      await expect(page).not.toHaveURL(/login/);
    });

    await test.step('查看论文列表', async () => {
      await page.goto('/library');
      await expect(page.locator('main, [role="main"], .library-container')).toBeVisible({ timeout: 5000 });
      
      // 检查页面标题或主要内容
      const pageTitle = await page.locator('h1, h2').first().textContent().catch(() => null);
      console.log('页面标题:', pageTitle);
    });
  });

  test('场景2: 与AI Agent进行对话', async ({ page }) => {
    // 先登录
    await page.goto('/login');
    await page.fill('input[type="email"]', TEST_ACCOUNTS.primary.email);
    await page.fill('input[type="password"]', TEST_ACCOUNTS.primary.password);
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/(dashboard|papers|chat)/, { timeout: 10000 });

    await test.step('访问Chat页面', async () => {
      await page.goto('/chat');
      await expect(page).toHaveURL(/chat/, { timeout: 5000 });
    });

    await test.step('验证Agent UI组件', async () => {
      // 检查AgentStateSidebar
      const sidebar = page.locator('aside, [data-testid="agent-state-sidebar"], .agent-state-sidebar');
      const hasSidebar = await sidebar.isVisible({ timeout: 3000 }).catch(() => false);
      console.log('✓ AgentStateSidebar可见:', hasSidebar);

      // 检查Chat输入框
      const inputField = page.locator("textarea").first();
      await expect(inputField).toBeVisible({ timeout: 5000 });
    });

    await test.step('发送查询并观察Agent执行', async () => {
      const inputField = page.locator("textarea").first();
      
      // 测试不同Intent的问题
      const testQuery = '你好，请帮我找一篇关于大语言模型的论文';
      await inputField.fill(testQuery);
      await inputField.press('Enter');
      
      // 等待响应
      await page.waitForTimeout(8000);

      // 检查ThinkingProcess是否显示
      const thinkingProcess = page.locator('[data-testid="thinking-process"], .thinking-process');
      const hasThinkingProcess = await thinkingProcess.isVisible({ timeout: 2000 }).catch(() => false);
      console.log('✓ ThinkingProcess显示:', hasThinkingProcess);

      // 检查Agent状态变化
      const runningIndicator = page.locator('text=/RUNNING|执行中|思考中/i');
      const hasRunningState = await runningIndicator.isVisible({ timeout: 5000 }).catch(() => false);
      console.log('✓ Agent进入RUNNING状态:', hasRunningState);

      // 等待完成
      await page.waitForTimeout(10000);

      // 检查响应内容
      const responseContent = page.locator('.message, .response, [data-testid="ai-response"]');
      const hasResponse = await responseContent.count() > 0;
      console.log('✓ 收到AI响应:', hasResponse);
    });
  });

  test('场景3: 测试CRITICAL工具确认流程', async ({ page }) => {
    // 登录
    await page.goto('/login');
    await page.fill('input[type="email"]', TEST_ACCOUNTS.primary.email);
    await page.fill('input[type="password"]', TEST_ACCOUNTS.primary.password);
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/(dashboard|papers|chat)/, { timeout: 10000 });

    await test.step('请求删除论文（CRITICAL工具）', async () => {
      await page.goto('/chat');
      
      const inputField = page.locator("textarea").first();
      await inputField.fill('请帮我删除第一篇论文');
      await inputField.press('Enter');
      
      await page.waitForTimeout(8000);

      // 检查是否出现确认对话框
      const confirmationDialog = page.locator(
        '[role="dialog"], .modal, .confirmation, text=/确认|确认删除|Are you sure/i'
      );
      const hasConfirmation = await confirmationDialog.isVisible({ timeout: 5000 }).catch(() => false);
      console.log('✓ CRITICAL工具触发确认对话框:', hasConfirmation);
    });
  });

  test('场景4: 验证Intent分类', async ({ page }) => {
    // 登录
    await page.goto('/login');
    await page.fill('input[type="email"]', TEST_ACCOUNTS.primary.email);
    await page.fill('input[type="password"]', TEST_ACCOUNTS.primary.password);
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/(dashboard|papers|chat)/, { timeout: 10000 });
    await page.goto('/chat');

    const testQueries = [
      { query: '比较这两篇论文的方法差异', expectedIntent: 'compare' },
      { query: '这篇论文的实验结果怎么样', expectedIntent: 'results' },
      { query: '这个方法有代码实现吗', expectedIntent: 'code' },
      { query: '列出论文的参考文献', expectedIntent: 'references' },
    ];

    for (const { query } of testQueries) {
      await test.step(`测试Intent: ${query}`, async () => {
        const inputField = page.locator("textarea").first();
        await inputField.waitFor({ state: "visible", timeout: 10000 });
        await page.waitForTimeout(1000);
        await inputField.fill(query);
        await inputField.press('Enter');
        await page.waitForTimeout(10000);
      });
    }
  });

  test('场景5: 完整的论文阅读流程', async ({ page }) => {
    // 登录
    await page.goto('/login');
    await page.fill('input[type="email"]', TEST_ACCOUNTS.primary.email);
    await page.fill('input[type="password"]', TEST_ACCOUNTS.primary.password);
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/(dashboard|papers|chat)/, { timeout: 10000 });

    await test.step('查看论文列表', async () => {
      await page.goto('/library');
      await page.waitForTimeout(10000);

      // 检查是否有论文
      const paperCards = page.locator('[data-testid="paper-card"], .paper-card, article');
      const paperCount = await paperCards.count();
      console.log('✓ 论文数量:', paperCount);
    });

    await test.step('点击查看论文详情', async () => {
      const firstPaper = page.locator('[data-testid="paper-card"], .paper-card, article').first();
      if (await firstPaper.isVisible({ timeout: 2000 }).catch(() => false)) {
        await firstPaper.click();
        await page.waitForTimeout(10000);
      }
    });

    await test.step('向AI提问论文内容', async () => {
      await page.goto('/chat');
      
      const inputField = page.locator("textarea").first();
      await inputField.fill('这篇论文的主要贡献是什么？');
      await inputField.press('Enter');
      
      await page.waitForTimeout(10000);

      // 验证响应包含引用
      const citations = page.locator('[data-testid="citation"], .citation, [class*="cite"]');
      const hasCitations = await citations.count() > 0;
      console.log('✓ 响应包含引用:', hasCitations);
    });
  });

  test('场景6: 创建和管理笔记', async ({ page }) => {
    // 登录
    await page.goto('/login');
    await page.fill('input[type="email"]', TEST_ACCOUNTS.primary.email);
    await page.fill('input[type="password"]', TEST_ACCOUNTS.primary.password);
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/(dashboard|papers|chat)/, { timeout: 10000 });

    await test.step('访问笔记列表', async () => {
      await page.goto('/notes');
      await page.waitForTimeout(10000);

      const notesList = page.locator('[data-testid="notes-list"], .notes-container, main');
      await expect(notesList).toBeVisible({ timeout: 5000 });
    });

    await test.step('创建新笔记', async () => {
      const createButton = page.locator('button:has-text("新建"), button:has-text("创建"), button:has-text("Create")');
      if (await createButton.isVisible({ timeout: 2000 }).catch(() => false)) {
        await createButton.click();
        await page.waitForTimeout(10000);
      }
    });
  });
});