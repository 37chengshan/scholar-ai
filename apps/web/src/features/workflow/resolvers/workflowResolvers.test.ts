import { describe, expect, it } from 'vitest';
import { resolveNextActions, resolveRecoverableActions, resolveStatusBadge, resolveWorkflowCopy } from '@/features/workflow/resolvers/workflowResolvers';
import type { WorkflowRun } from '@/features/workflow/types';

const baseRun: WorkflowRun = {
  id: 'run-1',
  source: 'chat',
  status: 'running',
  stage: 'reasoning',
  error: null,
  nextAction: null,
  updatedAt: new Date().toISOString(),
};

describe('workflowResolvers', () => {
  it('resolves pending actions for running run', () => {
    const actions = resolveNextActions(baseRun);
    expect(actions.length).toBe(1);
    expect(actions[0].label).toContain('Monitor');
  });

  it('resolves recoverable action for failed run', () => {
    const failed = { ...baseRun, status: 'failed' as const, error: 'network timeout' };
    const actions = resolveRecoverableActions(failed);
    expect(actions.length).toBe(1);
    expect(actions[0].description).toContain('network timeout');
  });

  it('resolves status badge and copy keys', () => {
    expect(resolveStatusBadge('waiting').tone).toBe('warning');
    expect(resolveWorkflowCopy('artifacts')).toContain('Artifacts');
  });
});
