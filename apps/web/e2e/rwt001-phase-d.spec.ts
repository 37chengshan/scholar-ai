import { expect, test } from '@playwright/test';

type ReviewDraftRecord = {
  id: string;
  runId?: string | null;
  title?: string | null;
  status?: string | null;
  draftDoc?: {
    sections?: Array<{
      heading?: string | null;
      paragraphs?: Array<{
        text?: string | null;
      }>;
    }>;
  } | null;
};

type ReviewRunDetailRecord = {
  id: string;
  status?: string | null;
  steps?: Array<{
    step_name?: string | null;
    status?: string | null;
  }>;
};

async function askOneTurn(page: any, question: string): Promise<void> {
  const textarea = page.locator('textarea').first();

  await expect(textarea).toBeVisible({ timeout: 20_000 });
  await textarea.fill(question);
  await textarea.press('Enter');

  let enteredStreamingState = false;
  try {
    await expect(textarea).toBeDisabled({ timeout: 15_000 });
    enteredStreamingState = true;
  } catch {
    enteredStreamingState = false;
  }

  const placeholderVisible = await page
    .getByText(/思考中|thinking/i)
    .first()
    .isVisible()
    .catch(() => false);

  await expect(textarea).toBeEnabled({ timeout: 240_000 });
  expect(enteredStreamingState || placeholderVisible).toBeTruthy();
}

async function expectChatComposerUsable(page: any): Promise<void> {
  const textarea = page.locator('textarea').first();
  await expect(textarea).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText('Request failed')).toHaveCount(0, { timeout: 20_000 });
}

test.describe('Phase D RWT-001', () => {
  test('runs the D-001 search to KB to read to notes chat review chain with real services', async ({ page }) => {
    test.setTimeout(900_000);

    const kbName = `PhaseD-RWT001-${Date.now()}`;
    const query = 'Attention Is All You Need';
    const email = `phase-d-rwt001-${Date.now()}@example.com`;
    const password = 'Pr19E2EPass123';
    const name = 'Phase D RWT001';
    let kbId = '';
    let paperId = '';
    let importJobId = '';
    let reviewDraftId = '';
    let reviewRunId = '';
    let reviewDraftStatus = '';
    const existingDraftIds = new Set<string>();

    await test.step('register a fresh isolated account', async () => {
      await page.goto('/register');
      await page.waitForLoadState('domcontentloaded');
      await page.locator('input[type="text"]').first().fill(name);
      await page.locator('input[type="email"]').first().fill(email);
      await page.locator('input[type="password"]').nth(0).fill(password);
      await page.locator('input[type="password"]').nth(1).fill(password);
      await page.locator('button[type="submit"]').click();
      await page.waitForURL(/\/dashboard/, { timeout: 30_000 });
    });

    await test.step('create a fresh knowledge base', async () => {
      await page.goto('/knowledge-bases');
      await expect(page.getByRole('button', { name: '创建知识库' }).first()).toBeVisible({ timeout: 15_000 });

      await page.getByRole('button', { name: '创建知识库' }).first().click();
      await page.fill('#kb-name', kbName);
      await page.fill('#kb-desc', 'Phase D RWT-001 real validation chain for D-001.');
      await page.getByRole('button', { name: '创建知识库' }).last().click();

      const kbCard = page.locator('[data-kb-id]').filter({ hasText: kbName }).first();
      await expect(kbCard).toBeVisible({ timeout: 30_000 });
      kbId = (await kbCard.getAttribute('data-kb-id')) || '';
      expect(kbId).toBeTruthy();
    });

    await test.step('search the real paper in external search', async () => {
      await page.goto('/search');
      await expect(page.getByTestId('search-query-input')).toBeVisible({ timeout: 15_000 });
      await page.getByTestId('search-query-input').fill(query);
      await page.getByTestId('search-query-button').click();

      await expect(page.getByTestId('search-results-panel')).toBeVisible({ timeout: 60_000 });
      await expect(page.getByTestId('search-result-card').filter({ hasText: query }).first()).toBeVisible({ timeout: 90_000 });
    });

    await test.step('import the paper into the fresh knowledge base', async () => {
      const targetCard = page
        .getByTestId('search-result-card')
        .filter({
          has: page.getByRole('heading', { name: /^Attention is All you Need$/i }),
        })
        .filter({ hasText: '2017' })
        .filter({
          has: page.getByRole('button', { name: 'Import paper into library' }),
        })
        .first();

      await expect(targetCard).toBeVisible({ timeout: 60_000 });
      await targetCard.getByRole('button', { name: 'Import paper into library' }).click();

      const importModal = page.locator('div.fixed.inset-0.bg-black\\/50').last();
      await expect(importModal.getByText('选择知识库导入')).toBeVisible({ timeout: 15_000 });
      await importModal.getByRole('button', { name: new RegExp(kbName) }).click();
      await expect(importModal.getByRole('button', { name: '确认导入到该知识库' })).toBeEnabled({
        timeout: 15_000,
      });
      await importModal.getByRole('button', { name: '确认导入到该知识库' }).click();
    });

    await test.step('wait for the real import job to be created', async () => {
      await expect
        .poll(async () => {
          const response = await page.request.get(`/api/v1/import-jobs?knowledgeBaseId=${kbId}&limit=20`);
          if (!response.ok()) {
            return '';
          }
          const payload = await response.json();
          const jobs = payload?.data?.jobs ?? [];
          const latest = jobs[0];
          importJobId = latest?.importJobId ?? latest?.id ?? '';
          return importJobId;
        }, {
          timeout: 30_000,
          intervals: [500, 1000, 2000],
        })
        .not.toBe('');
    });

    await test.step('wait for import completion and open the KB papers tab', async () => {
      await expect
        .poll(async () => {
          const response = await page.request.get(`/api/v1/import-jobs/${importJobId}`);
          if (!response.ok()) {
            return 'pending';
          }
          const payload = await response.json();
          const job = payload?.data ?? payload;
          if (job?.status === 'failed' || job?.status === 'cancelled') {
            return job.status;
          }
          return job?.status === 'completed' ? 'completed' : 'pending';
        }, {
          timeout: 420_000,
          intervals: [1000, 3000, 5000],
        })
        .toBe('completed');

      if (!page.url().includes(`/knowledge-bases/${kbId}`)) {
        await page.goto(`/knowledge-bases/${kbId}?tab=papers`);
      }

      await expect(page).toHaveURL(new RegExp(`/knowledge-bases/${kbId}\\?tab=papers`), { timeout: 30_000 });
      await expect(page.getByRole('tab', { name: /论文列表/i })).toBeVisible({ timeout: 30_000 });
      await expect(page.getByRole('button', { name: '阅读' }).first()).toBeVisible({ timeout: 60_000 });
      await expect(page.getByText(/Attention is All you Need/i).first()).toBeVisible({ timeout: 60_000 });
    });

    await test.step('open the imported paper in read view', async () => {
      await page.getByRole('button', { name: '阅读' }).first().click();
      await page.waitForURL(/\/read\//, { timeout: 30_000 });
      await expect(page).toHaveURL(/\/read\//);
      paperId = page.url().split('/read/')[1]?.split('?')[0] || '';
      expect(paperId).toBeTruthy();

      await expect(page.getByText('Request failed')).toHaveCount(0, { timeout: 20_000 });
      await expect(page.getByRole('tab', { name: /AI总结/i })).toBeVisible({ timeout: 60_000 });
    });

    await test.step('wait for real reading notes to become available in AI summary', async () => {
      await page.getByRole('tab', { name: /AI总结/i }).click();
      await expect(page.getByTestId('ai-summary-panel')).toBeVisible({ timeout: 15_000 });

      await expect
        .poll(async () => {
          const response = await page.request.get(`/api/v1/papers/${paperId}/summary`);
          if (!response.ok()) {
            return false;
          }

          const payload = await response.json();
          const summary = payload?.data ?? payload;
          const notes = summary?.summary ?? summary?.readingNotes ?? summary?.reading_notes ?? null;
          return typeof notes === 'string' && notes.trim().length > 0;
        }, {
          timeout: 420_000,
          intervals: [2000, 5000],
        })
        .toBeTruthy();
    });

    await test.step('ask one real single-paper chat turn', async () => {
      await page.goto(`/chat?paperId=${paperId}`);
      await expectChatComposerUsable(page);
      await askOneTurn(page, '请用中文总结这篇论文的核心问题、方法和主要结论。');
    });

    await test.step('generate one real KB review draft and wait for run trace', async () => {
      await page.goto(`/knowledge-bases/${kbId}?tab=review`);
      await expect(page.getByRole('heading', { name: 'Review Draft' })).toBeVisible({ timeout: 20_000 });
      await expect(page.getByRole('button', { name: '生成 Outline + Draft' })).toBeVisible({ timeout: 20_000 });

      const existingDraftsResponse = await page.request.get(
        `/api/v1/knowledge-bases/${kbId}/review-drafts?limit=20&offset=0`,
      );
      if (existingDraftsResponse.ok()) {
        const existingDraftsPayload = await existingDraftsResponse.json();
        const existingDrafts: ReviewDraftRecord[] = existingDraftsPayload?.data?.items ?? [];
        for (const draft of existingDrafts) {
          if (draft.id) {
            existingDraftIds.add(draft.id);
          }
        }
      }

      await page.getByRole('button', { name: '生成 Outline + Draft' }).click();

      await expect
        .poll(async () => {
          const draftsResponse = await page.request.get(
            `/api/v1/knowledge-bases/${kbId}/review-drafts?limit=20&offset=0`,
          );
          if (!draftsResponse.ok()) {
            return false;
          }

          const draftsPayload = await draftsResponse.json();
          const drafts: ReviewDraftRecord[] = draftsPayload?.data?.items ?? [];
          const draft = drafts.find((item) => item.id && !existingDraftIds.has(item.id));
          if (!draft?.id) {
            return false;
          }

          reviewDraftId = draft.id;
          reviewRunId = draft.runId || '';
          reviewDraftStatus = draft.status || '';
          if (draft.status === 'failed') {
            return false;
          }
          if (draft.status === 'completed' || draft.status === 'partial') {
            return true;
          }
          return false;
        }, {
          timeout: 300_000,
          intervals: [1000, 3000, 5000],
        })
        .toBeTruthy();

      expect(reviewDraftId).toBeTruthy();
      expect(reviewRunId).toBeTruthy();
      expect(['completed', 'partial']).toContain(reviewDraftStatus);

      await expect
        .poll(async () => {
          const runResponse = await page.request.get(`/api/v1/runs/${reviewRunId}`);
          if (!runResponse.ok()) {
            return 'pending';
          }

          const runPayload = await runResponse.json();
          const run: ReviewRunDetailRecord | undefined = runPayload?.data;
          if (!run?.id) {
            return 'pending';
          }
          if (run.status === 'failed') {
            return 'failed';
          }
          if (run.status !== 'completed') {
            return 'pending';
          }

          const completedSteps =
            run.steps?.filter((step) => step.status === 'completed').map((step) => step.step_name || '') || [];
          const hasFinalizer = completedSteps.includes('draft_finalizer');
          return hasFinalizer ? 'completed' : 'pending';
        }, {
          timeout: 120_000,
          intervals: [1000, 3000, 5000],
        })
        .toBe('completed');

      await page.goto(`/knowledge-bases/${kbId}?tab=review&runId=${reviewRunId}`);
      await expect(page.getByText('Request failed')).toHaveCount(0, { timeout: 20_000 });
      await expect(page.getByText(/run_id:/i)).toBeVisible({ timeout: 30_000 });
      await expect(page.getByText(/draft_finalizer/i)).toBeVisible({ timeout: 30_000 });
    });
  });
});
