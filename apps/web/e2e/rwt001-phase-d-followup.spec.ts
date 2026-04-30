import { expect, test } from '@playwright/test';

type ReviewDraftRecord = {
  id: string;
  runId?: string | null;
  status?: string | null;
  draftDoc?: {
    sections?: Array<{
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

async function login(page: any, email: string, password: string): Promise<void> {
  await page.goto('/login');
  await page.waitForLoadState('domcontentloaded');

  if (/\/(dashboard|knowledge-bases|chat)/.test(page.url())) {
    return;
  }

  await page.locator('input[type="email"]').first().fill(email);
  await page.locator('input[type="password"]').first().fill(password);
  await page.locator('button[type="submit"]').click();
  await page.waitForURL(/\/(dashboard|knowledge-bases|chat)/, { timeout: 30_000 });
}

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

test.describe('Phase D RWT-001 follow-up', () => {
  test('reuses the imported real paper for read notes chat review', async ({ page }) => {
    test.setTimeout(600_000);

    const email = process.env.RWT001_FOLLOWUP_EMAIL ?? 'phase-d-rwt001-1777442659673@example.com';
    const password = process.env.RWT001_FOLLOWUP_PASSWORD ?? 'Pr19E2EPass123';
    const kbId = process.env.RWT001_FOLLOWUP_KB_ID ?? '89376111-88a1-4ae6-a4e9-703665f87e82';
    const paperId = process.env.RWT001_FOLLOWUP_PAPER_ID ?? '4a2a0cd9-d4b5-44e4-83b1-7b00a02922ed';
    let reviewDraftId = '';
    let reviewRunId = '';
    let reviewDraftStatus = '';
    const existingDraftIds = new Set<string>();

    await test.step('login with the real imported account', async () => {
      await login(page, email, password);
    });

    await test.step('open the KB papers tab and confirm the imported paper is present', async () => {
      await page.goto(`/knowledge-bases/${kbId}?tab=papers`);
      await expect(page.getByRole('tab', { name: /论文列表/i })).toBeVisible({ timeout: 30_000 });
      await expect(page.getByRole('button', { name: '阅读' }).first()).toBeVisible({ timeout: 60_000 });
      await expect(page.getByText(/Attention is All you Need/i).first()).toBeVisible({ timeout: 60_000 });
    });

    await test.step('open read view and confirm the AI summary surface is usable', async () => {
      await page.goto(`/read/${paperId}`);
      await expect(page.getByText('Request failed')).toHaveCount(0, { timeout: 20_000 });
      await expect(page.getByRole('tab', { name: /AI总结/i })).toBeVisible({ timeout: 60_000 });
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
          timeout: 120_000,
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
          return completedSteps.includes('draft_finalizer') ? 'completed' : 'pending';
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
