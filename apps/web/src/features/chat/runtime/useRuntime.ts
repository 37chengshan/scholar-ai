/**
 * useRuntime Hook — Bridges SSE stream events into AgentRun state.
 *
 * Per 战役 B WP2: Wraps useChatStream, intercepts Run protocol events,
 * and maintains a parallel AgentRun state via chatRuntime reducer.
 */

import { useReducer, useCallback, useMemo } from 'react';
import {
  runReducer,
  createInitialRun,
  mapSSEToRunAction,
  type RunAction,
} from '@/features/chat/runtime/chatRuntime';
import type { AgentRun, RecoveryState } from '@/features/chat/types/run';
import type { CanonicalSSEEventEnvelope } from '@/features/chat/adapters/sseEventAdapter';

// Run protocol event types that chatRuntime handles
const RUN_PROTOCOL_EVENTS = new Set([
  'run_start',
  'run_phase_change',
  'step_start',
  'step_complete',
  'run_complete',
  'recovery_available',
  'evidence',
  'artifact',
]);

export interface UseRuntimeReturn {
  /** Current AgentRun state */
  run: AgentRun;
  /** Dispatch a run action directly */
  dispatchRun: (action: RunAction) => void;
  /** Process a normalized SSE event — returns true if consumed */
  ingestEvent: (envelope: CanonicalSSEEventEnvelope) => boolean;
  /** Reset run state */
  resetRun: () => void;
  /** Current recovery state */
  recovery: RecoveryState;
}

export function useRuntime(): UseRuntimeReturn {
  const [run, dispatchRun] = useReducer(runReducer, createInitialRun());

  const ingestEvent = useCallback(
    (envelope: CanonicalSSEEventEnvelope): boolean => {
      if (!RUN_PROTOCOL_EVENTS.has(envelope.event_type)) {
        return false;
      }
      const action = mapSSEToRunAction(envelope.event_type, envelope.data);
      if (action) {
        dispatchRun(action);
        return true;
      }
      return false;
    },
    []
  );

  const resetRun = useCallback(() => {
    dispatchRun({ type: 'RUN_RESET' });
  }, []);

  const recovery = useMemo<RecoveryState>(() => ({
    available: run.recoverable,
    actions: run.pendingActions.map(a => a.type),
    context: {},
  }), [run.recoverable, run.pendingActions]);

  return { run, dispatchRun, ingestEvent, resetRun, recovery };
}
