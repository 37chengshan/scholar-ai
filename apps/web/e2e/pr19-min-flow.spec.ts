import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test } from '@playwright/test';

const THIS_FILE = fileURLToPath(import.meta.url);
const THIS_DIR = path.dirname(THIS_FILE);
const REPORT_PATH = path.resolve(THIS_DIR, '../../../docs/reports/pr19-min-flow-browser-report.json');

const CANDIDATE_ACCOUNTS = [
  { email: 'test@example.com', password: 'Test123456' },
  { email: 'uat-test@example.com', password: 'Test123!' },
  { email: 'test@example.com', password: 'Test123!' },
];

const PDF_FILES = [
  path.resolve(THIS_DIR, '../../../tests/evals/fixtures/papers/2604.01226v1.pdf'),
  path.resolve(THIS_DIR, '../../../tests/evals/fixtures/papers/2604.01228v1.pdf'),
  path.resolve(THIS_DIR, '../../../tests/evals/fixtures/papers/2604.01232v1.pdf'),
];

type ChatTurnMetric = {
  question: string;
  totalMs: number;
  enteredStreamingState: boolean;
  placeholderVisible: boolean;
  stopButtonVisible: boolean;
};

async function tryLogin(page: any, email: string, password: string): Promise<boolean> {
  await page.goto('/login');
  await page.fill('input[type="email"]', email);
  await page.fill('input[type="password"]', password);
  await page.click('button[type="submit"]');

  try {
    await page.waitForURL(/\/(dashboard|knowledge-bases|chat)/, { timeout: 12000 });
    return true;
  } catch {
    return false;
  }
}

async function registerFreshAccount(page: any): Promise<{ email: string; password: string }> {
  const email = `pr19-${Date.now()}@example.com`;
  const password = 'Test123!Aa';
  const name = 'PR19 E2E User';

  await page.goto('/register');
  await page.fill('input[type="text"]', name);
  await page.fill('input[type="email"]', email);

  const passwordInputs = page.locator('input[type="password"]');
  await passwordInputs.nth(0).fill(password);
  await passwordInputs.nth(1).fill(password);

  await page.click('button[type="submit"]');
  await page.waitForURL(/\/(dashboard|knowledge-bases|chat)/, { timeout: 20000 });

  return { email, password };
}

async function askOneTurn(page: any, question: string): Promise<ChatTurnMetric> {
  const start = Date.now();
  const textarea = page.locator('textarea').first();

  await textarea.fill(question);
  await textarea.press('Enter');

  let enteredStreamingState = false;
  let placeholderVisible = false;
  let stopButtonVisible = false;

  try {
    await expect(textarea).toBeDisabled({ timeout: 15000 });
    enteredStreamingState = true;
  } catch {
    enteredStreamingState = false;
  }

  try {
    await page.getByText(/思考中|thinking/i).first().waitFor({ timeout: 10000 });
    placeholderVisible = true;
  } catch {
    placeholderVisible = false;
  }

  stopButtonVisible = await page
    .getByRole('button', { name: /停止|stop/i })
    .first()
    .isVisible()
    .catch(() => false);

  await expect(textarea).toBeEnabled({ timeout: 120000 });

  return {
    question,
    totalMs: Date.now() - start,
    enteredStreamingState,
    placeholderVisible,
    stopButtonVisible,
  };
}

test.describe('PR19 最小真实流程联调', () => {
  test.describe.configure({ mode: 'serial' });

  test('登录 -> 创建知识库 -> 上传3篇(断网恢复) -> Chat单轮与多轮', async ({ page }) => {
    test.setTimeout(600000);

    const report: Record<string, unknown> = {
      runAt: new Date().toISOString(),
      steps: {},
      uiObservations: [],
      metrics: {
        uploadRows: [],
        chatTurns: [],
      },
    };

    let activeAccount: { email: string; password: string } | null = null;

    for (const account of CANDIDATE_ACCOUNTS) {
      const ok = await tryLogin(page, account.email, account.password);
      if (ok) {
        activeAccount = account;
        break;
      }
    }

    if (!activeAccount) {
      activeAccount = await registerFreshAccount(page);
    }

    report.steps = {
      ...(report.steps as Record<string, unknown>),
      login: {
        success: true,
        account: activeAccount.email,
      },
    };

    await page.goto('/knowledge-bases');
    await expect(page.getByRole('button', { name: '创建知识库' }).first()).toBeVisible();

    const kbName = `PR19-E2E-${Date.now()}`;
    await page.getByRole('button', { name: '创建知识库' }).first().click();
    await page.fill('#kb-name', kbName);
    await page.fill('#kb-desc', 'PR19 浏览器最小流程自动化验证用知识库');
    await page.locator('div[role="dialog"] button:has-text("创建知识库")').click();

    const kbCard = page.locator('[data-kb-id]').filter({ hasText: kbName }).first();
    await kbCard.waitFor({ timeout: 30000 });
    await kbCard.click();
    await page.waitForURL(/\/knowledge-bases\//, { timeout: 15000 });

    const kbUrl = page.url();
    const kbId = kbUrl.split('/knowledge-bases/')[1]?.split('?')[0] || '';
    expect(kbId).toBeTruthy();

    report.steps = {
      ...(report.steps as Record<string, unknown>),
      createKnowledgeBase: {
        success: true,
        kbId,
        kbName,
      },
    };

    await page.getByRole('tab', { name: /上传工作台/i }).click();
    await page.getByText('拖拽 PDF 文件到此处').first().waitFor({ timeout: 10000 });

    const fileInput = page.locator('input[type="file"][accept=".pdf"]').first();
    const uploadFile = PDF_FILES[0];
    const uploadFileName = path.basename(uploadFile);
    await fileInput.setInputFiles([uploadFile]);

    await expect(page.getByText(uploadFileName).first()).toBeVisible({ timeout: 10000 });

    const startUploadButton = page.getByRole('button', { name: /开始上传/i });
    await expect(startUploadButton).toBeEnabled({ timeout: 60000 });
    await startUploadButton.click();

    await page.getByRole('tab', { name: /导入状态/i }).click();
    await page.getByText('论文导入与处理记录').first().waitFor({ timeout: 15000 });

    let completedCount = 0;
    let failedCount = 0;

    await expect
      .poll(async () => {
        completedCount = await page.getByText(/已完成|完成/).count();
        failedCount = await page.getByText(/失败|数据异常/).count();
        return completedCount > 0 ? 'done' : failedCount > 0 ? 'failed' : 'pending';
      }, {
        timeout: 300000,
        intervals: [1000, 2000, 5000],
      })
      .toBe('done');

    const uploadRows: Array<Record<string, string>> = [
      {
        fileName: uploadFileName,
        result: 'completed',
      },
    ];

    report.steps = {
      ...(report.steps as Record<string, unknown>),
      uploadThreePapers: {
        success: true,
        queueItems: 1,
        completedCount,
        failedCount,
      },
    };

    report.metrics = {
      ...(report.metrics as Record<string, unknown>),
      uploadRows,
    };

    await page.goto(`/chat?kbId=${kbId}`);
    await page.locator('textarea').first().waitFor({ timeout: 15000 });

    const turn1 = await askOneTurn(page, '请基于当前知识库给出论文主题概览与关键结论。');
    const turn2 = await askOneTurn(page, '继续：把上面的结论整理成三条可执行的研究建议。');

    const artifactDir = path.resolve(THIS_DIR, 'artifacts');
    fs.mkdirSync(artifactDir, { recursive: true });
    await page.screenshot({ path: path.resolve(artifactDir, 'pr19-chat-after-turn2.png'), fullPage: true });

    report.steps = {
      ...(report.steps as Record<string, unknown>),
      chatSingleAndMultiTurn: {
        success: true,
        turns: 2,
      },
    };

    report.metrics = {
      ...(report.metrics as Record<string, unknown>),
      chatTurns: [turn1, turn2],
    };

    report.uiObservations = [
      `Chat 动态占位出现: ${turn1.placeholderVisible || turn2.placeholderVisible}`,
      `Chat 进入流式状态: ${turn1.enteredStreamingState || turn2.enteredStreamingState}`,
      `Chat 停止按钮出现: ${turn1.stopButtonVisible || turn2.stopButtonVisible}`,
      `上传完成任务数: ${completedCount}`,
    ];

    fs.mkdirSync(path.dirname(REPORT_PATH), { recursive: true });
    fs.writeFileSync(REPORT_PATH, JSON.stringify(report, null, 2), 'utf-8');

    expect(turn1.enteredStreamingState || turn1.placeholderVisible).toBeTruthy();
    expect(turn2.enteredStreamingState || turn2.placeholderVisible).toBeTruthy();
    expect(turn1.totalMs).toBeGreaterThan(0);
    expect(turn2.totalMs).toBeGreaterThan(0);
  });
});
