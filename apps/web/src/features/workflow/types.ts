export type WorkflowStatus = 'idle' | 'running' | 'waiting' | 'completed' | 'failed' | 'cancelled';

export interface WorkflowScope {
  type: 'global' | 'knowledge-base' | 'paper';
  id: string | null;
  title: string;
  subtitle?: string;
}

export interface WorkflowRun {
  id: string;
  source: 'chat' | 'search-import' | 'library-import' | 'read' | 'unknown';
  status: WorkflowStatus;
  stage: string;
  error: string | null;
  nextAction: string | null;
  updatedAt: string;
  traceId?: string | null;
  sessionId?: string | null;
  messageId?: string | null;
  scopeType?: WorkflowScope['type'];
  scopeId?: string | null;
  startedAt?: string | null;
  endedAt?: string | null;
  durationMs?: number | null;
  eventCount?: number;
  artifactCount?: number;
  tokensUsed?: number;
  cost?: number;
}

export interface WorkflowActionItem {
  id: string;
  label: string;
  description?: string;
  kind: 'primary' | 'secondary' | 'danger';
  intent?: 'primary' | 'neutral' | 'danger';
  action: 'open' | 'resume' | 'retry' | 'cancel' | 'dismiss' | 'reject';
  payload?: Record<string, unknown>;
}

export interface WorkflowArtifact {
  id: string;
  kind: 'answer' | 'citation' | 'note' | 'import-report' | 'session' | 'run-output';
  title: string;
  href?: string;
  context?: string;
  payload?: Record<string, unknown>;
}

export interface WorkflowTimelineItem {
  id: string;
  title: string;
  description: string;
  at: string;
  status?: WorkflowStatus | 'info';
  payload?: Record<string, unknown>;
}

export interface WorkflowStatusBadge {
  label: string;
  tone: 'default' | 'success' | 'warning' | 'danger' | 'muted';
}

export type WorkflowAction = WorkflowActionItem;
export type WorkflowTimelineEvent = WorkflowTimelineItem;

export interface WorkflowHydratedPayload {
  scope: WorkflowScope;
  currentRun: WorkflowRun | null;
  pendingActions: WorkflowActionItem[];
  recoverableTasks: WorkflowActionItem[];
  artifacts: WorkflowArtifact[];
  timeline: WorkflowTimelineItem[];
}
