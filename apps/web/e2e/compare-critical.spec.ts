import { expect, test } from '@playwright/test';
import { registerAndLogin } from './helpers/auth';

test.describe('Critical E2E - Compare', () => {
  test('compare page renders matrix from compare v4 response', async ({ page, request }) => {
    await registerAndLogin(page, request);

    const mockPaper = (id: string, title: string, year: number) => ({
      id,
      title,
      authors: ['Tester'],
      year,
      status: 'completed',
      created_at: '2026-04-28T00:00:00Z',
      updated_at: '2026-04-28T00:00:00Z',
    });

    await page.route('**/api/v1/papers/paper-1', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockPaper('paper-1', 'Paper One', 2024)) });
    });

    await page.route('**/api/v1/papers/paper-2', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockPaper('paper-2', 'Paper Two', 2025)) });
    });

    await page.route('**/api/v1/compare/v4', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            response_type: 'compare',
            answer_mode: 'partial',
            answer: '',
            claims: [],
            citations: [],
            evidence_blocks: [],
            quality: {
              citation_coverage: 1,
              unsupported_claim_rate: 0,
              answer_evidence_consistency: 1,
              fallback_used: false,
              fallback_reason: null,
            },
            trace_id: 'trace-compare-e2e',
            run_id: 'run-compare-e2e',
            compare_matrix: {
              paper_ids: ['paper-1', 'paper-2'],
              dimensions: [{ id: 'method', label: 'Method' }],
              rows: [
                {
                  paper_id: 'paper-1',
                  title: 'Paper One',
                  year: 2024,
                  cells: [
                    {
                      dimension_id: 'method',
                      content: 'Retriever-augmented transformer',
                      support_status: 'supported',
                      evidence_blocks: [
                        {
                          evidence_id: 'chunk-1',
                          source_type: 'paper',
                          paper_id: 'paper-1',
                          source_chunk_id: 'chunk-1',
                          page_num: 4,
                          section_path: 'method',
                          content_type: 'text',
                          text: 'Retriever-augmented transformer',
                          citation_jump_url: '/read/paper-1?page=4&source_id=chunk-1',
                        },
                      ],
                    },
                  ],
                },
                {
                  paper_id: 'paper-2',
                  title: 'Paper Two',
                  year: 2025,
                  cells: [
                    {
                      dimension_id: 'method',
                      content: 'Hybrid dense + sparse retrieval',
                      support_status: 'supported',
                      evidence_blocks: [
                        {
                          evidence_id: 'chunk-2',
                          source_type: 'paper',
                          paper_id: 'paper-2',
                          source_chunk_id: 'chunk-2',
                          page_num: 5,
                          section_path: 'method',
                          content_type: 'text',
                          text: 'Hybrid dense + sparse retrieval',
                          citation_jump_url: '/read/paper-2?page=5&source_id=chunk-2',
                        },
                      ],
                    },
                  ],
                },
              ],
              summary: '',
              cross_paper_insights: [],
            },
          },
        }),
      });
    });

    await page.waitForURL(/\/(dashboard|chat|knowledge-bases)/, { timeout: 20000 });
    await page.goto('/compare?paper_ids=paper-1,paper-2');

    await expect(page.getByText('Paper One')).toBeVisible({ timeout: 15000 });
    await expect(page.getByText('Paper Two')).toBeVisible({ timeout: 15000 });

    await page.getByRole('button', { name: /生成对比表|Generate Compare Table/i }).click();

    await expect(page.getByText('Retriever-augmented transformer')).toBeVisible({ timeout: 15000 });
    await expect(page.getByText('Hybrid dense + sparse retrieval')).toBeVisible({ timeout: 15000 });
    await expect(page.getByRole('button', { name: /带入 Chat 继续问|Continue in Chat/i })).toBeVisible();
  });
});
