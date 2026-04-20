import { describe, expect, it } from 'vitest';
import { mapImportJobToWorkflowCard, mapRunToWorkflowViewModel, mapScopeToBannerModel } from '@/features/workflow/adapters/workflowAdapters';

describe('workflowAdapters', () => {
  it('maps run payload to workflow run view model', () => {
    const run = mapRunToWorkflowViewModel({
      id: 'run-1',
      source: 'chat',
      status: 'running',
      stage: 'reasoning',
      nextAction: 'confirm',
    });

    expect(run.id).toBe('run-1');
    expect(run.status).toBe('running');
    expect(run.stage).toBe('reasoning');
    expect(run.nextAction).toBe('confirm');
  });

  it('maps import runtime to workflow card', () => {
    const card = mapImportJobToWorkflowCard({
      jobId: 'job-9',
      status: 'completed',
      stage: 'indexing',
    });

    expect(card).not.toBeNull();
    expect(card?.id).toBe('job-9');
    expect(card?.status).toBe('completed');
  });

  it('maps scope to banner model', () => {
    const banner = mapScopeToBannerModel({
      type: 'knowledge-base',
      id: 'kb-1',
      title: 'Library Workflow',
      subtitle: 'Scoped to kb-1',
    });

    expect(banner.title).toBe('Library Workflow');
    expect(banner.subtitle).toContain('kb-1');
  });
});
