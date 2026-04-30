import type { AgentRun, RunTimelineItem } from '@/features/chat/types/run';
import type { WorkflowActionItem, WorkflowArtifact, WorkflowRun, WorkflowScope, WorkflowTimelineItem } from '@/features/workflow/types';

const DEFAULT_UPDATED_AT = new Date(0).toISOString();

function toWorkflowStatus(status: string | null | undefined): WorkflowRun['status'] {
  switch (status) {
    case 'completed':
      return 'completed';
    case 'failed':
      return 'failed';
    case 'cancelled':
      return 'cancelled';
    case 'waiting_confirmation':
      return 'waiting';
    case 'running':
      return 'running';
    default:
      return 'idle';
  }
}

function inferWorkflowScopeType(scope: AgentRun['scope']): WorkflowScope['type'] {
  switch (scope) {
    case 'single_paper':
      return 'paper';
    case 'full_kb':
      return 'knowledge-base';
    default:
      return 'global';
  }
}

function computeDurationMs(startedAt?: string, endedAt?: string): number | null {
  if (!startedAt) {
    return null;
  }
  const start = new Date(startedAt).getTime();
  const end = endedAt ? new Date(endedAt).getTime() : Date.now();
  if (Number.isNaN(start) || Number.isNaN(end)) {
    return null;
  }
  return Math.max(end - start, 0);
}

function mapTimelineStatus(status?: string): WorkflowTimelineItem['status'] {
  switch (status) {
    case 'completed':
    case 'failed':
    case 'cancelled':
    case 'running':
      return status;
    case 'waiting':
      return 'waiting';
    default:
      return 'info';
  }
}

export function mapRunToWorkflowViewModel(partial: Partial<WorkflowRun> & Pick<WorkflowRun, 'id' | 'source'>): WorkflowRun {
  return {
    id: partial.id,
    source: partial.source,
    status: partial.status ?? 'running',
    stage: partial.stage ?? 'processing',
    error: partial.error ?? null,
    nextAction: partial.nextAction ?? null,
    updatedAt: partial.updatedAt ?? new Date().toISOString(),
    traceId: partial.traceId ?? null,
    sessionId: partial.sessionId ?? null,
    messageId: partial.messageId ?? null,
    scopeType: partial.scopeType,
    scopeId: partial.scopeId ?? null,
    startedAt: partial.startedAt ?? null,
    endedAt: partial.endedAt ?? null,
    durationMs: partial.durationMs ?? null,
    eventCount: partial.eventCount ?? 0,
    artifactCount: partial.artifactCount ?? 0,
    tokensUsed: partial.tokensUsed ?? 0,
    cost: partial.cost ?? 0,
  };
}

export function mapAgentRunToWorkflowViewModel(run: AgentRun): WorkflowRun | null {
  if (!run.runId) {
    return null;
  }

  return mapRunToWorkflowViewModel({
    id: run.runId,
    source: 'chat',
    status: toWorkflowStatus(run.status),
    stage: run.currentPhase || run.phase || 'running',
    error: run.outcome.error ?? null,
    nextAction: run.pendingActions[0]?.type ?? null,
    updatedAt: run.endedAt ?? run.startedAt ?? DEFAULT_UPDATED_AT,
    traceId: (run.outcome.finalSummary as Record<string, unknown> | undefined)?.traceId as string | null | undefined ?? null,
    sessionId: run.sessionId,
    messageId: run.messageId,
    scopeType: inferWorkflowScopeType(run.scope),
    scopeId: null,
    startedAt: run.startedAt ?? null,
    endedAt: run.endedAt ?? null,
    durationMs: computeDurationMs(run.startedAt, run.endedAt),
    eventCount: run.timeline.length + run.toolEvents.length,
    artifactCount: run.artifacts.length,
    tokensUsed: run.outcome.finalSummary?.tokensUsed ?? 0,
    cost: run.outcome.finalSummary?.cost ?? 0,
  });
}

export function mapImportJobToWorkflowCard(job: {
  jobId: string;
  status: string;
  stage?: string | null;
  traceId?: string | null;
  updatedAt?: string | null;
  startedAt?: string | null;
  completedAt?: string | null;
}): WorkflowRun {
  return mapRunToWorkflowViewModel({
    id: job.jobId,
    source: 'search-import',
    status: toWorkflowStatus(job.status),
    stage: job.stage || 'import',
    error: null,
    nextAction: job.status === 'failed' ? 'Retry import' : 'Monitor import progress',
    updatedAt: job.updatedAt ?? new Date().toISOString(),
    traceId: job.traceId ?? null,
    scopeType: 'global',
    scopeId: null,
    startedAt: job.startedAt ?? null,
    endedAt: job.completedAt ?? null,
    durationMs: computeDurationMs(job.startedAt ?? undefined, job.completedAt ?? undefined),
  });
}

function formatPendingActionLabel(type: AgentRun['pendingActions'][number]['type']) {
  switch (type) {
    case 'confirm':
      return 'Confirm';
    case 'reject':
      return 'Reject';
    case 'retry':
      return 'Retry';
    case 'resume':
      return 'Resume';
    case 'cancel':
      return 'Cancel';
    default:
      return 'Open';
  }
}

function formatPendingActionDescription(action: AgentRun['pendingActions'][number]) {
  if (typeof action.params?.reason === 'string' && action.params.reason.trim().length > 0) {
    return action.params.reason;
  }
  if (action.impactSummary) {
    return action.impactSummary;
  }
  if (action.tool) {
    return `Action required for ${action.tool}.`;
  }
  return 'Review the pending action in context before continuing.';
}

export function mapPendingActionsToWorkflowActions(actions: AgentRun['pendingActions']): WorkflowActionItem[] {
  return actions.map((action) => ({
    id: action.id,
    label: formatPendingActionLabel(action.type),
    description: formatPendingActionDescription(action),
    kind: action.type === 'cancel' || action.type === 'reject' ? 'danger' : 'primary',
    intent: action.type === 'cancel' || action.type === 'reject' ? 'danger' : 'primary',
    action: action.type === 'confirm' ? 'open' : action.type,
    payload: action.params,
  }));
}

export function mapArtifactToUiRenderable(artifact: WorkflowArtifact): WorkflowArtifact {
  return artifact;
}

export function mapAgentRunArtifacts(run: AgentRun): WorkflowArtifact[] {
  const artifacts: WorkflowArtifact[] = run.artifacts.map((artifact) => ({
    id: artifact.id,
    kind: artifact.type === 'citation' ? 'citation' : artifact.type === 'note' ? 'note' : 'run-output',
    title: artifact.title,
    href: artifact.url,
    payload: artifact.payload,
    context: artifact.content,
  }));

  const evidenceArtifacts = run.evidence.map((item, index) => ({
    id: `evidence-${item.sourceId}-${index}`,
    kind: 'citation' as const,
    title: item.title,
    context: item.textPreview,
    payload: {
      sourceId: item.sourceId,
      pageNum: item.pageNum,
      sectionPath: item.sectionPath,
      relevance: item.relevance,
      consistency: item.consistency,
    },
  }));

  return [...artifacts, ...evidenceArtifacts];
}

export function mapAgentRunTimeline(run: AgentRun): WorkflowTimelineItem[] {
  return run.timeline.map((item: RunTimelineItem) => ({
    id: item.id,
    title: item.label,
    description: item.label,
    at: new Date(item.timestamp).toISOString(),
    status: mapTimelineStatus(item.status),
    payload: item.metadata,
  }));
}

export function mapChatScopeToWorkflowScope(scope: { type?: string | null; id?: string | null }): WorkflowScope {
  if (scope.type === 'single_paper') {
    return {
      type: 'paper',
      id: scope.id ?? null,
      title: 'Paper Workflow',
      subtitle: scope.id ? `Focused workflow for ${scope.id}` : 'Focused workflow for a single paper',
    };
  }

  if (scope.type === 'full_kb') {
    return {
      type: 'knowledge-base',
      id: scope.id ?? null,
      title: 'Knowledge Workflow',
      subtitle: scope.id ? `Knowledge-base workflow for ${scope.id}` : 'Knowledge-base workflow context',
    };
  }

  return {
    type: 'global',
    id: scope.id ?? null,
    title: 'Global Workspace',
    subtitle: 'Track pending work and output artifacts',
  };
}

export function mapScopeToBannerModel(scope: WorkflowScope | null | undefined): Pick<WorkflowScope, 'title' | 'subtitle'> {
  if (!scope) {
    return {
      title: 'Global Workspace',
      subtitle: 'Track pending work and output artifacts',
    };
  }

  return {
    title: scope.title,
    subtitle: scope.subtitle ?? '',
  };
}
