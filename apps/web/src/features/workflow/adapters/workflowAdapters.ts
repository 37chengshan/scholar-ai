import type {
  WorkflowAction,
  WorkflowArtifact,
  WorkflowBannerModel,
  WorkflowRun,
  WorkflowScope,
  WorkflowStatus,
  WorkflowTimelineEvent,
} from '@/features/workflow/types';
import type { AgentRun, PendingAction, RunEvidence } from '@/features/chat/types/run';

interface RawImportRuntime {
  jobId?: string;
  status?: string;
  stage?: string;
  error?: string | null;
  nextAction?: Record<string, unknown> | null;
}

export function mapRunToWorkflowViewModel(run: {
  id: string;
  source: WorkflowRun['source'];
  status?: string;
  stage?: string;
  error?: string | null;
  nextAction?: string | null;
}): WorkflowRun {
  const normalizedStatus = normalizeStatus(run.status);
  return {
    id: run.id,
    source: run.source,
    status: normalizedStatus,
    stage: run.stage || 'running',
    error: run.error ?? null,
    nextAction: run.nextAction ?? null,
    updatedAt: new Date().toISOString(),
  };
}

export function mapImportJobToWorkflowCard(runtime: RawImportRuntime): WorkflowRun | null {
  if (!runtime.jobId) {
    return null;
  }

  return mapRunToWorkflowViewModel({
    id: runtime.jobId,
    source: 'search-import',
    status: runtime.status,
    stage: runtime.stage || 'import',
    error: runtime.error ?? null,
    nextAction: runtime.nextAction ? JSON.stringify(runtime.nextAction) : null,
  });
}

export function mapErrorToUiAction(error: string | null | undefined): { label: string; description: string } | null {
  if (!error) {
    return null;
  }

  return {
    label: 'Resolve Failure',
    description: error,
  };
}

export function mapArtifactToUiRenderable(input: {
  id: string;
  kind: WorkflowArtifact['kind'];
  title: string;
  context?: string;
  href?: string;
}): WorkflowArtifact {
  return {
    id: input.id,
    kind: input.kind,
    title: input.title,
    context: input.context,
    href: input.href,
  };
}

export function mapScopeToBannerModel(scope: WorkflowScope): WorkflowBannerModel {
  return {
    title: scope.title,
    subtitle: scope.subtitle || 'Track status, actions, and evidence in one place.',
  };
}

export function mapAgentRunToWorkflowViewModel(run: AgentRun): WorkflowRun | null {
  if (!run.runId) {
    return null;
  }

  return {
    id: run.runId,
    source: 'chat',
    status: normalizeStatus(run.status),
    stage: run.phase,
    error: run.outcome.error ?? null,
    nextAction: run.pendingActions[0]?.type ?? null,
    updatedAt: run.endedAt || run.startedAt || new Date().toISOString(),
  };
}

export function mapChatScopeToWorkflowScope(scope: {
  type: 'single_paper' | 'full_kb' | 'general' | 'error' | null;
  id: string | null;
  title?: string;
  errorMessage?: string;
}): WorkflowScope {
  if (scope.type === 'single_paper') {
    return {
      type: 'paper',
      id: scope.id,
      title: scope.title || 'Paper Scope',
      subtitle: scope.title ? `Focused QA for ${scope.title}` : 'Focused QA for a single paper',
    };
  }

  if (scope.type === 'full_kb') {
    return {
      type: 'knowledge-base',
      id: scope.id,
      title: scope.title || 'Library Scope',
      subtitle: scope.title ? `Full KB reasoning for ${scope.title}` : 'Full knowledge base reasoning',
    };
  }

  if (scope.type === 'error') {
    return {
      type: 'run',
      id: scope.id,
      title: 'Scope Error',
      subtitle: scope.errorMessage || 'The current chat scope is invalid.',
    };
  }

  return {
    type: 'global',
    id: null,
    title: 'Global Workspace',
    subtitle: 'Cross-library research workflow',
  };
}

export function mapPendingActionsToWorkflowActions(actions: PendingAction[]): WorkflowAction[] {
  return actions.map((action) => ({
    id: action.id,
    label: action.type.toUpperCase(),
    description: action.impactSummary || `Run action: ${action.type}`,
    intent: action.type === 'retry' || action.type === 'cancel' ? 'danger' : 'primary',
  }));
}

export function mapAgentRunArtifacts(run: AgentRun): WorkflowArtifact[] {
  const evidenceArtifacts = run.evidence.map((item: RunEvidence) => ({
    id: `evidence-${item.sourceId}`,
    kind: 'citation' as const,
    title: item.title,
    context: item.textPreview,
  }));

  const runtimeArtifacts = run.artifacts.map((artifact) => {
    const kind: WorkflowArtifact['kind'] = artifact.type === 'note'
      ? 'note'
      : artifact.type === 'citation'
        ? 'citation'
        : 'answer';

    return {
      id: artifact.id,
      kind,
      title: artifact.title,
      context: artifact.content || artifact.type,
      href: artifact.url,
    };
  });

  return [...runtimeArtifacts, ...evidenceArtifacts];
}

export function mapAgentRunTimeline(run: AgentRun): WorkflowTimelineEvent[] {
  return run.timeline.slice(-8).map((item) => ({
    id: item.id,
    title: item.label,
    description: item.status || item.type,
    at: new Date(item.timestamp).toISOString(),
  }));
}

function normalizeStatus(status: string | undefined): WorkflowStatus {
  switch ((status || '').toLowerCase()) {
    case 'running':
    case 'processing':
      return 'running';
    case 'waiting':
    case 'waiting_confirmation':
    case 'waiting_for_user':
      return 'waiting';
    case 'failed':
      return 'failed';
    case 'completed':
    case 'success':
      return 'completed';
    case 'cancelled':
    case 'canceled':
      return 'cancelled';
    default:
      return 'idle';
  }
}
