/**
 * Run Protocol Types — Agent-Native runtime contract (frontend).
 *
 * Mirrors backend Run/Step/ToolEvent/Artifact/Evidence models.
 * Per 战役 B WP5: deterministic UI contract.
 */

// ── Run Phase (state machine) ────────────────────────────

export type RunPhase =
  | 'idle'
  | 'planning'
  | 'executing'
  | 'waiting_for_user'
  | 'verifying'
  | 'completed'
  | 'failed'
  | 'cancelled';

export type RunStatus =
  | 'idle'
  | 'running'
  | 'waiting_confirmation'
  | 'completed'
  | 'failed'
  | 'cancelled';

export type RunScope = 'general' | 'single_paper' | 'full_kb';

// ── Step ─────────────────────────────────────────────────

export type StepType =
  | 'analyze'
  | 'retrieve'
  | 'read'
  | 'tool_call'
  | 'synthesize'
  | 'verify'
  | 'confirm';

export type StepStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'skipped'
  | 'waiting';

export interface RunStep {
  stepId: string;
  runId: string;
  type: StepType;
  title: string;
  description: string;
  status: StepStatus;
  order: number;
  startedAt?: string;
  endedAt?: string;
  verificationStatus?: 'pass' | 'fail' | 'skip';
}

// ── Tool Event ───────────────────────────────────────────

export interface ToolEvent {
  eventId: string;
  runId: string;
  stepId: string;
  toolName: string;
  eventType: 'call' | 'result' | 'error';
  label: string;
  args: Record<string, unknown>;
  result?: Record<string, unknown>;
  summary?: string;
  startedAt?: string;
  endedAt?: string;
  status: 'running' | 'success' | 'failed';
}

// ── Timeline ─────────────────────────────────────────────

export interface RunTimelineItem {
  id: string;
  type: 'phase' | 'tool' | 'step' | 'confirmation' | 'done' | 'error' | 'recovery';
  label: string;
  timestamp: number;
  status?: string;
  metadata?: Record<string, unknown>;
}

// ── Confirmation ─────────────────────────────────────────

export interface ConfirmationRequest {
  confirmationId: string;
  runId: string;
  stepId: string;
  reason: string;
  riskLevel: 'low' | 'medium' | 'high';
  proposedAction: string;
  toolName: string;
  payload: Record<string, unknown>;
  expiresAt?: string;
}

// ── Pending Action ───────────────────────────────────────

export interface PendingAction {
  id: string;
  type: 'confirm' | 'reject' | 'retry' | 'resume' | 'cancel';
  tool?: string;
  riskLevel?: 'low' | 'medium' | 'high';
  impactSummary?: string;
  params?: Record<string, unknown>;
}

// ── Evidence ─────────────────────────────────────────────

export interface RunEvidence {
  sourceId: string;
  title: string;
  pageNum?: number;
  sectionPath?: string;
  anchorText?: string;
  textPreview: string;
  relevance?: number;
  consistency?: number;
}

// ── Artifact ─────────────────────────────────────────────

export type ArtifactType =
  | 'citation'
  | 'note'
  | 'summary'
  | 'file'
  | 'extracted_result'
  | 'download'
  | 'tool_output'
  | 'result';

export interface RunArtifact {
  id: string;
  type: ArtifactType;
  title: string;
  payload?: Record<string, unknown>;
  content?: string;
  url?: string;
}

// ── Final Summary ────────────────────────────────────────

export interface FinalSummary {
  answer: string;
  citations: RunEvidence[];
  artifacts: RunArtifact[];
  answerEvidenceConsistency?: number;
  lowConfidenceReasons: string[];
  stepSummary: Array<Record<string, unknown>>;
  tokensUsed: number;
  cost: number;
}

// ── Run Outcome ──────────────────────────────────────────

export interface RunOutcome {
  summary?: string;
  error?: string;
  finalSummary?: FinalSummary;
  queryFamily?: string;
  plannerQueryCount?: number;
  decontextualizedQuery?: string;
  secondPassUsed?: boolean;
  secondPassGain?: number;
  evidenceBundleHitCount?: number;
}

// ── Agent Run (full state) ───────────────────────────────

export interface AgentRun {
  runId: string | null;
  sessionId: string | null;
  messageId: string | null;
  scope: RunScope;
  mode: 'auto' | 'rag' | 'agent';
  status: RunStatus;
  phase: RunPhase;
  currentPhase: string;
  objective: string;
  startedAt?: string;
  endedAt?: string;
  steps: RunStep[];
  toolEvents: ToolEvent[];
  timeline: RunTimelineItem[];
  pendingActions: PendingAction[];
  confirmation: ConfirmationRequest | null;
  artifacts: RunArtifact[];
  evidence: RunEvidence[];
  outcome: RunOutcome;
  recoverable: boolean;
}

// ── Recovery ─────────────────────────────────────────────

export type RecoveryAction = 'retry' | 'resume' | 'cancel' | 'confirm' | 'reject';

export interface RecoveryState {
  available: boolean;
  actions: RecoveryAction[];
  context: Record<string, unknown>;
}
