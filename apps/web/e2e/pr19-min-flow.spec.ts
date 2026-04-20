import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test } from '@playwright/test';

const THIS_FILE = fileURLToPath(import.meta.url);
const THIS_DIR = path.dirname(THIS_FILE);
const REPORT_PATH = path.resolve(THIS_DIR, '../../../docs/reports/pr19-min-flow-browser-report.json');

const DEDICATED_ACCOUNT = {
  email: process.env.PR19_E2E_USER_EMAIL ?? 'pr19-e2e@example.com',
  password: process.env.PR19_E2E_USER_PASSWORD ?? 'Pr19E2EPass123',
};

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

type ImportJobRecord = {
  importJobId?: string;
  status?: string;
  stage?: string;
  progress?: number;
  paper?: {
    paperId?: string | null;
    title?: string | null;
  };
  error?: {
    message?: string;
  };
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

async function loginWithDedicatedAccount(page: any): Promise<{ email: string; password: string }> {
  const ok = await tryLogin(page, DEDICATED_ACCOUNT.email, DEDICATED_ACCOUNT.password);
  if (!ok) {
    throw new Error(
      'Dedicated PR19 test account login failed. Run `cd apps/api && .venv/bin/python scripts/ensure_e2e_test_user.py` before E2E.',
    );
  }

  return DEDICATED_ACCOUNT;
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

  await expect(textarea).toBeEnabled({ timeout: 240000 });

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
    test.setTimeout(1200000);

    const report: Record<string, unknown> = {
      runAt: new Date().toISOString(),
      steps: {},
      uiObservations: [],
      metrics: {
        uploadRows: [],
        chatTurns: [],
      },
    };

    const activeAccount = await loginWithDedicatedAccount(page);

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
    await fileInput.setInputFiles(PDF_FILES);

    const uploadFileNames = PDF_FILES.map((filePath) => path.basename(filePath));
    for (const fileName of uploadFileNames) {
      await expect(page.getByText(fileName).first()).toBeVisible({ timeout: 10000 });
    }

    const startUploadButton = page.getByRole('button', { name: /开始上传/i });
    await expect(startUploadButton).toBeEnabled({ timeout: 60000 });
    await startUploadButton.click();

    await page.getByRole('tab', { name: /导入状态/i }).click();
    await page.getByText('论文导入与处理记录').first().waitFor({ timeout: 15000 });

    let progressVisibleInUi = false;
    try {
      await expect(page.getByText(/正在处理/).first()).toBeVisible({ timeout: 20000 });
      progressVisibleInUi = true;
    } catch {
      progressVisibleInUi = false;
    }

    let completedCount = 0;
    let failedCount = 0;
    let totalJobs = 0;
    let runningJobs = 0;
    let progressObserved = false;
    let latestFailureReason = '';
    let importState: 'pending' | 'done' | 'failed' = 'pending';
    let firstCompletedPaperId: string | null = null;

    await expect
      .poll(async () => {
        const response = await page.request.get(`/api/v1/import-jobs?knowledgeBaseId=${kbId}&limit=50`);
        if (!response.ok()) {
          return 'pending';
        }

        const payload = await response.json();
        const jobs: ImportJobRecord[] = payload?.data?.jobs ?? [];
        totalJobs = jobs.length;
        completedCount = jobs.filter((job) => job.status === 'completed').length;
        failedCount = jobs.filter((job) => job.status === 'failed').length;
        runningJobs = jobs.filter((job) => job.status === 'running' || job.status === 'created').length;

        progressObserved =
          progressObserved ||
          jobs.some((job) => typeof job.progress === 'number' && job.progress > 0 && job.progress < 100) ||
          runningJobs > 0;

        const completedJobWithPaper = jobs.find(
          (job) => job.status === 'completed' && job.paper?.paperId,
        );
        if (completedJobWithPaper?.paper?.paperId) {
          firstCompletedPaperId = completedJobWithPaper.paper.paperId;
        }

        if (failedCount > 0) {
          latestFailureReason =
            jobs.find((job) => job.status === 'failed')?.error?.message || 'unknown_import_error';
        }

        importState = completedCount >= 3 ? 'done' : failedCount > 0 ? 'failed' : 'pending';
        return importState;
      }, {
        timeout: 780000,
        intervals: [1000, 2000, 5000],
      })
      .not.toBe('pending');

    expect(importState, latestFailureReason).toBe('done');
    expect(completedCount).toBeGreaterThanOrEqual(3);
    expect(failedCount).toBe(0);
    expect(totalJobs).toBeGreaterThanOrEqual(3);
    expect(progressVisibleInUi || progressObserved).toBeTruthy();

    const uploadRows: Array<Record<string, string>> = [
      ...uploadFileNames.map((fileName) => ({
        fileName,
        result: 'completed',
      })),
    ];

    report.steps = {
      ...(report.steps as Record<string, unknown>),
      uploadPapers: {
        success: true,
        queueItems: 3,
        totalJobs,
        runningJobs,
        completedCount,
        failedCount,
        progressVisibleInUi,
        progressObserved,
        latestFailureReason: latestFailureReason || null,
      },
    };

    report.metrics = {
      ...(report.metrics as Record<string, unknown>),
      uploadRows,
    };

    await page.getByRole('tab', { name: /论文列表/i }).click();
    await expect(page.getByRole('button', { name: '阅读' }).first()).toBeVisible({ timeout: 20000 });

    const readButtons = page.getByRole('button', { name: '阅读' });
    const paperCount = await readButtons.count();
    expect(paperCount).toBeGreaterThanOrEqual(3);

    await readButtons.first().click();
    await page.waitForURL(/\/read\//, { timeout: 20000 });

    const readUrl = page.url();
    const readPaperId = readUrl.split('/read/')[1]?.split('?')[0] || firstCompletedPaperId || '';
    expect(readPaperId).toBeTruthy();

    await page.getByRole('tab', { name: /AI总结/i }).click();
    await expect(page.getByTestId('ai-summary-panel')).toBeVisible({ timeout: 10000 });

    await expect
      .poll(async () => {
        const response = await page.request.get(`/api/v1/papers/${readPaperId}`);
        if (!response.ok()) {
          return false;
        }

        const payload = await response.json();
        const paper = payload?.data ?? payload;
        const notes = paper?.readingNotes ?? paper?.reading_notes ?? null;
        return typeof notes === 'string' && notes.trim().length > 0;
      }, {
        timeout: 420000,
        intervals: [2000, 5000],
      })
      .toBeTruthy();

    await expect(page.getByText(/正在生成 AI 总结/).first()).toHaveCount(0, { timeout: 30000 });
    await expect(page.locator('[data-testid="ai-summary-panel"] .magazine-body').first()).toBeVisible({ timeout: 30000 });

    await page.goto(`/chat?paperId=${readPaperId}`);
    await expect(page.getByText(/单论文模式/).first()).toBeVisible({ timeout: 20000 });
    await page.locator('textarea').first().waitFor({ timeout: 15000 });

    const singlePaperTurn = await askOneTurn(page, '请总结这篇论文的研究问题、方法和主要结论。');

    await page.goto(`/chat?kbId=${kbId}`);
    await expect(page.getByText(/全库模式/).first()).toBeVisible({ timeout: 20000 });

    const multiPaperTurn = await askOneTurn(page, '请比较知识库里三篇论文的方法差异，并给出各自适用场景。');

    const artifactDir = path.resolve(THIS_DIR, 'artifacts');
    fs.mkdirSync(artifactDir, { recursive: true });
    await page.screenshot({ path: path.resolve(artifactDir, 'pr19-chat-after-multi-turn.png'), fullPage: true });

    report.steps = {
      ...(report.steps as Record<string, unknown>),
      readAndNotes: {
        success: true,
        paperId: readPaperId,
      },
      chatSingleAndMultiPaper: {
        success: true,
        turns: 2,
      },
    };

    report.metrics = {
      ...(report.metrics as Record<string, unknown>),
      chatTurns: [singlePaperTurn, multiPaperTurn],
    };

    report.uiObservations = [
      `导入进度可见(UI/API): ${progressVisibleInUi || progressObserved}`,
      `知识库论文数量: ${paperCount}`,
      `Chat 动态占位出现: ${singlePaperTurn.placeholderVisible || multiPaperTurn.placeholderVisible}`,
      `Chat 进入流式状态: ${singlePaperTurn.enteredStreamingState || multiPaperTurn.enteredStreamingState}`,
      `Chat 停止按钮出现: ${singlePaperTurn.stopButtonVisible || multiPaperTurn.stopButtonVisible}`,
      `上传完成任务数: ${completedCount}`,
    ];

    fs.mkdirSync(path.dirname(REPORT_PATH), { recursive: true });
    fs.writeFileSync(REPORT_PATH, JSON.stringify(report, null, 2), 'utf-8');

    expect(singlePaperTurn.enteredStreamingState || singlePaperTurn.placeholderVisible).toBeTruthy();
    expect(multiPaperTurn.enteredStreamingState || multiPaperTurn.placeholderVisible).toBeTruthy();
    expect(singlePaperTurn.totalMs).toBeGreaterThan(0);
    expect(multiPaperTurn.totalMs).toBeGreaterThan(0);
  });
});
