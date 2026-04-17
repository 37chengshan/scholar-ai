export type RunStatus =
  | 'idle'
  | 'running'
  | 'waiting_confirmation'
  | 'completed'
  | 'failed'
  | 'cancelled';

export type RunScope = 'general' | 'single_paper' | 'full_kb';

export interface RunTimelineItem {
  id: string;
  type: 'phase' | 'tool' | 'confirmation' | 'done' | 'error';
  label: string;
  timestamp: number;
  metadata?: Record<string, unknown>;
}

export interface PendingAction {
  id: string;
  tool?: string;
  riskLevel?: 'low' | 'medium' | 'high';
  impactSummary?: string;
  params?: Record<string, unknown>;
}

export interface RunArtifact {
  id: string;
  type: 'citation' | 'tool_output' | 'result';
  title: string;
  payload?: Record<string, unknown>;
}

export interface RunOutcome {
  summary?: string;
  error?: string;
}

export interface AgentRun {
  runId: string | null;
  sessionId: string | null;
  messageId: string | null;
  scope: RunScope;
  mode: 'auto' | 'rag' | 'agent';
  status: RunStatus;
  currentPhase: string;
  timeline: RunTimelineItem[];
  pendingActions: PendingAction[];
  artifacts: RunArtifact[];
  outcome: RunOutcome;
}
