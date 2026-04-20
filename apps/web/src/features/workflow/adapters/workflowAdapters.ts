import type {
  WorkflowArtifact,
  WorkflowBannerModel,
  WorkflowRun,
  WorkflowScope,
  WorkflowStatus,
} from '@/features/workflow/types';

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

function normalizeStatus(status: string | undefined): WorkflowStatus {
  switch ((status || '').toLowerCase()) {
    case 'running':
    case 'processing':
      return 'running';
    case 'waiting':
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
