import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test } from '@playwright/test';

const THIS_FILE = fileURLToPath(import.meta.url);
const THIS_DIR = path.dirname(THIS_FILE);
const REPORT_PATH = path.resolve(THIS_DIR, '../../../docs/reports/pr19-stepwise-flow-report.json');

function loadPreviousState(): Partial<{
  kbId: string;
  kbName: string;
  paperId: string;
  uploadCompleted: number;
  uploadFailed: number;
  notesReady: boolean;
  chatTurns: ChatTurnMetric[];
}> {
  try {
    if (!fs.existsSync(REPORT_PATH)) {
      return {};
    }
    const raw = fs.readFileSync(REPORT_PATH, 'utf-8');
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    return {
      kbId: typeof parsed.kbId === 'string' ? parsed.kbId : '',
      kbName: typeof parsed.kbName === 'string' ? parsed.kbName : '',
      paperId: typeof parsed.paperId === 'string' ? parsed.paperId : '',
      uploadCompleted: typeof parsed.uploadCompleted === 'number' ? parsed.uploadCompleted : 0,
      uploadFailed: typeof parsed.uploadFailed === 'number' ? parsed.uploadFailed : 0,
      notesReady: Boolean(parsed.notesReady),
      chatTurns: Array.isArray(parsed.chatTurns) ? (parsed.chatTurns as ChatTurnMetric[]) : [],
    };
  } catch {
    return {};
  }
}

const previousState = loadPreviousState();

const DEDICATED_ACCOUNT = {
  email: process.env.PR19_E2E_USER_EMAIL ?? 'pr19-e2e@example.com',
  password: process.env.PR19_E2E_USER_PASSWORD ?? 'Pr19E2EPass123',
};

const PDF_FILES = [
  path.resolve(THIS_DIR, '../../../tests/evals/fixtures/papers/2604.01226v1.pdf'),
  path.resolve(THIS_DIR, '../../../tests/evals/fixtures/papers/2604.01228v1.pdf'),
  path.resolve(THIS_DIR, '../../../tests/evals/fixtures/papers/2604.01232v1.pdf'),
];

type ImportJobRecord = {
  status?: string;
  progress?: number;
  paper?: {
    paperId?: string | null;
  };
  error?: {
    message?: string;
  };
};

type ChatTurnMetric = {
  question: string;
  totalMs: number;
  enteredStreamingState: boolean;
  placeholderVisible: boolean;
};

const flowState: {
  kbId: string;
  kbName: string;
  paperId: string;
  uploadCompleted: number;
  uploadFailed: number;
  notesReady: boolean;
  chatTurns: ChatTurnMetric[];
} = {
  kbId: previousState.kbId ?? '',
  kbName: previousState.kbName ?? '',
  paperId: previousState.paperId ?? '',
  uploadCompleted: previousState.uploadCompleted ?? 0,
  uploadFailed: previousState.uploadFailed ?? 0,
  notesReady: previousState.notesReady ?? false,
  chatTurns: previousState.chatTurns ?? [],
};

async function loginWithDedicatedAccount(page: any): Promise<void> {
  await page.goto('/login');
  await page.fill('input[type="email"]', DEDICATED_ACCOUNT.email);
  await page.fill('input[type="password"]', DEDICATED_ACCOUNT.password);
  await page.click('button[type="submit"]');
  await page.waitForURL(/\/(dashboard|knowledge-bases|chat)/, { timeout: 20000 });
}

async function askOneTurn(page: any, question: string): Promise<ChatTurnMetric> {
  const start = Date.now();
  const textarea = page.locator('textarea').first();

  await textarea.fill(question);
  await textarea.press('Enter');

  let enteredStreamingState = false;
  let placeholderVisible = false;

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

  await expect(textarea).toBeEnabled({ timeout: 240000 });

  return {
    question,
    totalMs: Date.now() - start,
    enteredStreamingState,
    placeholderVisible,
  };
}

test.describe('PR19 分步节点验证', () => {
  test.describe.configure({ mode: 'serial' });

  test('节点1: 专用测试用户登录', async ({ page }) => {
    await loginWithDedicatedAccount(page);
    await expect(page.getByText(/知识库|Dashboard|会话/i).first()).toBeVisible({ timeout: 10000 });
  });

  test('节点2: 创建知识库', async ({ page }) => {
    await loginWithDedicatedAccount(page);
    await page.goto('/knowledge-bases');

    const kbName = `PR19-STEP-${Date.now()}`;
    await page.getByRole('button', { name: '创建知识库' }).first().click();
    await page.fill('#kb-name', kbName);
    await page.fill('#kb-desc', 'PR19 分步节点验证知识库');
    await page.locator('div[role="dialog"] button:has-text("创建知识库")').click();

    const kbCard = page.locator('[data-kb-id]').filter({ hasText: kbName }).first();
    await kbCard.waitFor({ timeout: 30000 });
    await kbCard.click();
    await page.waitForURL(/\/knowledge-bases\//, { timeout: 15000 });

    const kbId = page.url().split('/knowledge-bases/')[1]?.split('?')[0] || '';
    expect(kbId).toBeTruthy();

    flowState.kbId = kbId;
    flowState.kbName = kbName;
  });

  test('节点3: 上传3篇论文并看到进度', async ({ page }) => {
    test.setTimeout(900000);
    expect(flowState.kbId).toBeTruthy();

    await loginWithDedicatedAccount(page);
    await page.goto(`/knowledge-bases/${flowState.kbId}`);

    await page.getByRole('tab', { name: /上传工作台/i }).click();
    await page.getByText('拖拽 PDF 文件到此处').first().waitFor({ timeout: 10000 });

    const fileInput = page.locator('input[type="file"][accept=".pdf"]').first();
    await fileInput.setInputFiles(PDF_FILES);

    const startUploadButton = page.getByRole('button', { name: /开始上传/i });
    await expect(startUploadButton).toBeEnabled({ timeout: 60000 });
    await startUploadButton.click();

    await page.getByRole('tab', { name: /导入状态/i }).click();
    await page.getByText('论文导入与处理记录').first().waitFor({ timeout: 15000 });
    await expect(page.getByText(/正在处理/).first()).toBeVisible({ timeout: 20000 });

    let completedCount = 0;
    let failedCount = 0;

    await expect
      .poll(async () => {
        const response = await page.request.get(`/api/v1/import-jobs?knowledgeBaseId=${flowState.kbId}&limit=50`);
        if (!response.ok()) {
          return 'pending';
        }

        const payload = await response.json();
        const jobs: ImportJobRecord[] = payload?.data?.jobs ?? [];

        completedCount = jobs.filter((job) => job.status === 'completed').length;
        failedCount = jobs.filter((job) => job.status === 'failed').length;

        const firstCompleted = jobs.find((job) => job.status === 'completed' && job.paper?.paperId)?.paper?.paperId;
        if (firstCompleted) {
          flowState.paperId = firstCompleted;
        }

        if (completedCount >= 3) {
          return 'done';
        }
        if (failedCount > 0) {
          return 'failed';
        }
        return 'pending';
      }, {
        timeout: 780000,
        intervals: [1000, 2000, 5000],
      })
      .toBe('done');

    flowState.uploadCompleted = completedCount;
    flowState.uploadFailed = failedCount;

    expect(flowState.uploadCompleted).toBeGreaterThanOrEqual(3);
    expect(flowState.uploadFailed).toBe(0);
  });

  test('节点4: 论文列表可读并显示总结笔记', async ({ page }) => {
    test.setTimeout(600000);
    expect(flowState.kbId).toBeTruthy();

    await loginWithDedicatedAccount(page);
    await page.goto(`/knowledge-bases/${flowState.kbId}`);

    await page.getByRole('tab', { name: /论文列表/i }).click();
    await expect(page.getByRole('button', { name: '阅读' }).first()).toBeVisible({ timeout: 20000 });

    await page.getByRole('button', { name: '阅读' }).first().click();
    await page.waitForURL(/\/read\//, { timeout: 20000 });

    const readPaperId = page.url().split('/read/')[1]?.split('?')[0] || flowState.paperId;
    expect(readPaperId).toBeTruthy();
    flowState.paperId = readPaperId;

    await page.getByRole('tab', { name: /AI总结/i }).click();
    await expect(page.getByTestId('ai-summary-panel')).toBeVisible({ timeout: 10000 });

    await expect
      .poll(async () => {
        const response = await page.request.get(`/api/v1/papers/${flowState.paperId}`);
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

    flowState.notesReady = true;
  });

  test('节点5: RAG问答单篇/多篇都能看到消息', async ({ page }) => {
    test.setTimeout(600000);
    expect(flowState.kbId).toBeTruthy();
    expect(flowState.paperId).toBeTruthy();

    await loginWithDedicatedAccount(page);

    await page.goto(`/chat?paperId=${flowState.paperId}`);
    await expect(page.getByText(/单论文模式/).first()).toBeVisible({ timeout: 20000 });
    const singleTurn = await askOneTurn(page, '请总结这篇论文的研究问题、方法和主要结论。');

    await page.goto(`/chat?kbId=${flowState.kbId}`);
    await expect(page.getByText(/全库模式/).first()).toBeVisible({ timeout: 20000 });
    const multiTurn = await askOneTurn(page, '请比较知识库中三篇论文的方法差异，并给出各自适用场景。');

    flowState.chatTurns = [singleTurn, multiTurn];

    expect(singleTurn.enteredStreamingState || singleTurn.placeholderVisible).toBeTruthy();
    expect(multiTurn.enteredStreamingState || multiTurn.placeholderVisible).toBeTruthy();
  });

  test.afterAll(async () => {
    const report = {
      runAt: new Date().toISOString(),
      dedicatedAccount: DEDICATED_ACCOUNT.email,
      kbId: flowState.kbId,
      kbName: flowState.kbName,
      paperId: flowState.paperId,
      uploadCompleted: flowState.uploadCompleted,
      uploadFailed: flowState.uploadFailed,
      notesReady: flowState.notesReady,
      chatTurns: flowState.chatTurns,
    };

    fs.mkdirSync(path.dirname(REPORT_PATH), { recursive: true });
    fs.writeFileSync(REPORT_PATH, JSON.stringify(report, null, 2), 'utf-8');
  });
});
