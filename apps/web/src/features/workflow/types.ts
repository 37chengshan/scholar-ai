export type WorkflowStatus = 'idle' | 'running' | 'waiting' | 'failed' | 'completed' | 'cancelled';

export type WorkflowScopeType = 'global' | 'knowledge-base' | 'paper' | 'run';

export interface WorkflowScope {
  type: WorkflowScopeType;
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
}

export interface WorkflowAction {
  id: string;
  label: string;
  description: string;
  intent: 'primary' | 'neutral' | 'danger';
  href?: string;
}

export interface WorkflowArtifact {
  id: string;
  kind: 'answer' | 'citation' | 'note' | 'import-report' | 'session';
  title: string;
  context?: string;
  href?: string;
}

export interface WorkflowTimelineEvent {
  id: string;
  title: string;
  description: string;
  at: string;
}

export interface WorkflowHydratedPayload {
  scope: WorkflowScope;
  currentRun: WorkflowRun | null;
  pendingActions: WorkflowAction[];
  recoverableTasks: WorkflowAction[];
  artifacts: WorkflowArtifact[];
  timeline: WorkflowTimelineEvent[];
}

export interface WorkflowBannerModel {
  title: string;
  subtitle: string;
}

export interface WorkflowStatusBadge {
  label: string;
  tone: 'default' | 'success' | 'warning' | 'danger' | 'muted';
}
