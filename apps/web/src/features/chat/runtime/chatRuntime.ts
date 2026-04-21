/**
 * Chat Runtime — Agent-Native Run lifecycle manager.
 *
 * Per 战役 B WP1: All runtime events MUST pass through adapter/reducer/state machine.
 * Pages MUST NOT consume raw SSE envelopes.
 *
 * This module bridges the SSE event stream to the AgentRun state:
 * - Ingests normalized SSE events from the adapter
 * - Maintains deterministic AgentRun state via pure reducer
 * - Exposes actions for confirmation/retry/cancel
 */

import type {
  AgentRun,
  RunPhase,
  RunStatus,
  RunStep,
  ToolEvent,
  RunEvidence,
  RunArtifact,
  RunTimelineItem,
  PendingAction,
  ConfirmationRequest,
  FinalSummary,
  RecoveryState,
  StepType,
  StepStatus,
} from '@/features/chat/types/run';

// ── Actions ──────────────────────────────────────────────

export type RunAction =
  | { type: 'RUN_START'; runId: string; sessionId: string; messageId: string; scope: string; objective: string; mode: string }
  | { type: 'RUN_PHASE_CHANGE'; phase: RunPhase; label: string }
  | { type: 'STEP_START'; stepId: string; runId: string; stepType: StepType; title: string; description: string; order: number }
  | { type: 'STEP_COMPLETE'; stepId: string; status: StepStatus; verificationStatus?: string }
  | { type: 'TOOL_EVENT'; event: ToolEvent }
  | { type: 'EVIDENCE_ADD'; evidence: RunEvidence }
  | { type: 'ARTIFACT_ADD'; artifact: RunArtifact }
  | { type: 'CONFIRMATION_REQUEST'; confirmation: ConfirmationRequest }
  | { type: 'RECOVERY_AVAILABLE'; actions: string[]; context: Record<string, unknown> }
  | { type: 'RUN_COMPLETE'; status: string; finalSummary?: FinalSummary; tokensUsed: number; cost: number }
  | { type: 'RUN_RESET' };

// ── Initial State ────────────────────────────────────────

export function createInitialRun(): AgentRun {
  return {
    runId: null,
    sessionId: null,
    messageId: null,
    scope: 'general',
    mode: 'auto',
    status: 'idle',
    phase: 'idle',
    currentPhase: 'idle',
    objective: '',
    steps: [],
    toolEvents: [],
    timeline: [],
    pendingActions: [],
    confirmation: null,
    artifacts: [],
    evidence: [],
    outcome: {},
    recoverable: false,
  };
}

// ── Phase → Status mapping ───────────────────────────────

function phaseToStatus(phase: RunPhase): RunStatus {
  switch (phase) {
    case 'idle': return 'idle';
    case 'planning':
    case 'executing':
    case 'verifying':
      return 'running';
    case 'waiting_for_user': return 'waiting_confirmation';
    case 'completed': return 'completed';
    case 'failed': return 'failed';
    case 'cancelled': return 'cancelled';
    default: return 'running';
  }
}

// ── Reducer ──────────────────────────────────────────────

export function runReducer(state: AgentRun, action: RunAction): AgentRun {
  const now = new Date().toISOString();

  switch (action.type) {
    case 'RUN_START':
      return {
        ...createInitialRun(),
        runId: action.runId,
        sessionId: action.sessionId,
        messageId: action.messageId,
        scope: action.scope as AgentRun['scope'],
        mode: action.mode as AgentRun['mode'],
        status: 'running',
        phase: 'planning',
        currentPhase: 'planning',
        objective: action.objective,
        startedAt: now,
        timeline: [{
          id: `tl-run-start-${Date.now()}`,
          type: 'phase',
          label: 'Run started',
          timestamp: Date.now(),
          status: 'running',
        }],
      };

    case 'RUN_PHASE_CHANGE': {
      const newStatus = phaseToStatus(action.phase);
      const item: RunTimelineItem = {
        id: `tl-phase-${Date.now()}`,
        type: 'phase',
        label: action.label || action.phase,
        timestamp: Date.now(),
        status: action.phase,
      };
      return {
        ...state,
        phase: action.phase,
        currentPhase: action.phase,
        status: newStatus,
        timeline: [...state.timeline, item],
      };
    }

    case 'STEP_START': {
      const step: RunStep = {
        stepId: action.stepId,
        runId: action.runId,
        type: action.stepType,
        title: action.title,
        description: action.description,
        status: 'running',
        order: action.order,
        startedAt: now,
      };
      const item: RunTimelineItem = {
        id: `tl-step-${action.stepId}`,
        type: 'step',
        label: action.title,
        timestamp: Date.now(),
        status: 'running',
      };
      return {
        ...state,
        steps: [...state.steps, step],
        timeline: [...state.timeline, item],
      };
    }

    case 'STEP_COMPLETE': {
      const steps = state.steps.map(s =>
        s.stepId === action.stepId
          ? { ...s, status: action.status, endedAt: now, verificationStatus: action.verificationStatus as RunStep['verificationStatus'] }
          : s
      );
      const timeline = state.timeline.map(t =>
        t.id === `tl-step-${action.stepId}`
          ? { ...t, status: action.status }
          : t
      );
      return { ...state, steps, timeline };
    }

    case 'TOOL_EVENT': {
      const existing = state.toolEvents.find(e => e.eventId === action.event.eventId);
      const toolEvents = existing
        ? state.toolEvents.map(e => e.eventId === action.event.eventId ? action.event : e)
        : [...state.toolEvents, action.event];

      const item: RunTimelineItem = {
        id: `tl-tool-${action.event.eventId}`,
        type: 'tool',
        label: action.event.label || action.event.toolName,
        timestamp: Date.now(),
        status: action.event.status,
        metadata: { toolName: action.event.toolName, eventType: action.event.eventType },
      };

      // Only add timeline item for new events (calls)
      const shouldAddTimeline = action.event.eventType === 'call' && !existing;
      const timeline = shouldAddTimeline
        ? [...state.timeline, item]
        : state.timeline.map(t =>
            t.id === `tl-tool-${action.event.eventId}` ? { ...t, status: action.event.status } : t
          );

      return { ...state, toolEvents, timeline };
    }

    case 'EVIDENCE_ADD':
      return {
        ...state,
        evidence: [...state.evidence, action.evidence],
      };

    case 'ARTIFACT_ADD':
      return {
        ...state,
        artifacts: [...state.artifacts, action.artifact],
      };

    case 'CONFIRMATION_REQUEST': {
      const item: RunTimelineItem = {
        id: `tl-confirm-${Date.now()}`,
        type: 'confirmation',
        label: action.confirmation.reason,
        timestamp: Date.now(),
        status: 'waiting',
      };
      return {
        ...state,
        confirmation: action.confirmation,
        status: 'waiting_confirmation',
        phase: 'waiting_for_user',
        timeline: [...state.timeline, item],
      };
    }

    case 'RECOVERY_AVAILABLE': {
      const pendingActions: PendingAction[] = action.actions.map(a => ({
        id: `pa-${a}-${Date.now()}`,
        type: a as PendingAction['type'],
      }));
      const item: RunTimelineItem = {
        id: `tl-recovery-${Date.now()}`,
        type: 'recovery',
        label: 'Recovery available',
        timestamp: Date.now(),
        metadata: { actions: action.actions, context: action.context },
      };
      return {
        ...state,
        recoverable: true,
        pendingActions,
        timeline: [...state.timeline, item],
      };
    }

    case 'RUN_COMPLETE': {
      const status = action.status as RunStatus;
      const phase: RunPhase = status === 'completed' ? 'completed' : status === 'failed' ? 'failed' : 'cancelled';
      const item: RunTimelineItem = {
        id: `tl-done-${Date.now()}`,
        type: 'done',
        label: `Run ${action.status}`,
        timestamp: Date.now(),
        status: action.status,
      };
      return {
        ...state,
        status,
        phase,
        currentPhase: phase,
        endedAt: now,
        outcome: {
          ...state.outcome,
          finalSummary: action.finalSummary,
        },
        timeline: [...state.timeline, item],
      };
    }

    case 'RUN_RESET':
      return createInitialRun();

    default:
      return state;
  }
}

// ── SSE → RunAction mapper ───────────────────────────────

export function mapSSEToRunAction(
  eventType: string,
  data: Record<string, unknown>
): RunAction | null {
  switch (eventType) {
    case 'run_start':
      return {
        type: 'RUN_START',
        runId: (data.run_id as string) || '',
        sessionId: (data.session_id as string) || '',
        messageId: (data.message_id as string) || '',
        scope: (data.scope as string) || 'general',
        objective: (data.objective as string) || '',
        mode: (data.mode as string) || 'auto',
      };

    case 'run_phase_change':
      return {
        type: 'RUN_PHASE_CHANGE',
        phase: (data.phase as RunPhase) || 'executing',
        label: (data.label as string) || '',
      };

    case 'step_start':
      return {
        type: 'STEP_START',
        stepId: (data.step_id as string) || '',
        runId: (data.run_id as string) || '',
        stepType: (data.type as StepType) || 'analyze',
        title: (data.title as string) || '',
        description: (data.description as string) || '',
        order: (data.order as number) || 0,
      };

    case 'step_complete':
      return {
        type: 'STEP_COMPLETE',
        stepId: (data.step_id as string) || '',
        status: (data.status as StepStatus) || 'completed',
        verificationStatus: data.verification_status as string | undefined,
      };

    case 'run_complete':
      return {
        type: 'RUN_COMPLETE',
        status: (data.status as string) || 'completed',
        finalSummary: data.final_summary as FinalSummary | undefined,
        tokensUsed: (data.tokens_used as number) || 0,
        cost: (data.cost as number) || 0,
      };

    case 'recovery_available':
      return {
        type: 'RECOVERY_AVAILABLE',
        actions: (data.available_actions as string[]) || [],
        context: (data.context as Record<string, unknown>) || {},
      };

    case 'evidence':
      return {
        type: 'EVIDENCE_ADD',
        evidence: {
          sourceId: (data.source_id as string) || '',
          title: (data.title as string) || '',
          pageNum: data.page_num as number | undefined,
          sectionPath: data.section_path as string | undefined,
          anchorText: data.anchor_text as string | undefined,
          textPreview: (data.text_preview as string) || '',
          relevance: data.relevance as number | undefined,
          consistency: data.consistency as number | undefined,
        },
      };

    case 'artifact':
      return {
        type: 'ARTIFACT_ADD',
        artifact: {
          id: (data.artifact_id as string) || `art-${Date.now()}`,
          type: (data.type as RunArtifact['type']) || 'result',
          title: (data.title as string) || '',
          content: data.content as string | undefined,
          url: data.url as string | undefined,
          payload: data.metadata as Record<string, unknown> | undefined,
        },
      };

    default:
      return null;
  }
}
