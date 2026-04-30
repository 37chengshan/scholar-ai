import type { WorkflowAction, WorkflowRun, WorkflowStatusBadge } from '@/features/workflow/types';

export function resolveNextActions(run: WorkflowRun | null): WorkflowAction[] {
  if (!run) {
    return [];
  }

  if (run.status === 'running') {
    return [
      {
        id: `${run.id}-monitor`,
        label: 'Monitor Run',
        description: 'Watch stage updates and evidence stream in real-time.',
        intent: 'primary',
        kind: 'primary',
        action: 'open',
      },
    ];
  }

  if (run.status === 'waiting') {
    return [
      {
        id: `${run.id}-continue`,
        label: 'Continue',
        description: 'This run is waiting for your confirmation to proceed.',
        intent: 'primary',
        kind: 'primary',
        action: 'resume',
      },
    ];
  }

  if (run.status === 'failed') {
    return [
      {
        id: `${run.id}-retry`,
        label: 'Retry',
        description: 'Retry this step using the same scope context.',
        intent: 'danger',
        kind: 'danger',
        action: 'retry',
      },
    ];
  }

  if (run.status === 'completed') {
    return [
      {
        id: `${run.id}-review`,
        label: 'Review Artifacts',
        description: 'Inspect outputs and citations before accepting.',
        intent: 'neutral',
        kind: 'secondary',
        action: 'open',
      },
    ];
  }

  return [];
}

export function resolveRecoverableActions(run: WorkflowRun | null): WorkflowAction[] {
  if (!run || run.status !== 'failed') {
    return [];
  }

  return [
    {
      id: `${run.id}-recover`,
      label: 'Recover Task',
      description: run.error || 'Recover from the last failed step.',
      intent: 'danger',
      kind: 'danger',
      action: 'retry',
    },
  ];
}

export function resolveStatusBadge(status: WorkflowRun['status']): WorkflowStatusBadge {
  switch (status) {
    case 'running':
      return { label: 'RUNNING', tone: 'default' };
    case 'waiting':
      return { label: 'WAITING', tone: 'warning' };
    case 'failed':
      return { label: 'FAILED', tone: 'danger' };
    case 'completed':
      return { label: 'COMPLETED', tone: 'success' };
    case 'cancelled':
      return { label: 'CANCELLED', tone: 'muted' };
    default:
      return { label: 'IDLE', tone: 'muted' };
  }
}

export function resolveWorkflowCopy(type: 'scope' | 'pending' | 'recoverable' | 'artifacts'): string {
  switch (type) {
    case 'scope':
      return 'Current Scope';
    case 'pending':
      return 'Pending Actions';
    case 'recoverable':
      return 'Recoverable Tasks';
    case 'artifacts':
      return 'Artifacts & Evidence';
    default:
      return 'Workflow';
  }
}
