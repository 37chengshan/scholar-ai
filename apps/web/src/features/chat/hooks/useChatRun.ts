import { useMemo } from 'react';
import type { AgentRun, RunScope, RunStatus, RunPhase } from '@/features/chat/types/run';
import { useShallow } from 'zustand/react/shallow';
import { useChatWorkspaceStore } from '@/features/chat/state/chatWorkspaceStore';
import type { WorkspaceScope } from '@/features/chat/state/chatWorkspaceStore';

function deriveScope(scope: WorkspaceScope): RunScope {
  if (scope.type === 'single_paper') {
    return 'single_paper';
  }
  if (scope.type === 'full_kb') {
    return 'full_kb';
  }
  return 'general';
}

function derivePhase(status: RunStatus): RunPhase {
  if (status === 'running') {
    return 'executing';
  }
  if (status === 'waiting_confirmation') {
    return 'waiting_for_user';
  }
  if (status === 'completed') {
    return 'completed';
  }
  if (status === 'failed') {
    return 'failed';
  }
  if (status === 'cancelled') {
    return 'cancelled';
  }
  return 'idle';
}

export function useChatRun(): { activeRun: AgentRun } {
  const {
    scope,
    mode,
    selectedSessionId,
    selectedMessageId,
    selectedRunId,
    activeRunStatus,
    pendingActions,
  } = useChatWorkspaceStore(
    useShallow((state) => ({
      scope: state.scope,
      mode: state.mode,
      selectedSessionId: state.selectedSessionId,
      selectedMessageId: state.selectedMessageId,
      selectedRunId: state.selectedRunId,
      activeRunStatus: state.activeRunStatus,
      pendingActions: state.pendingActions,
    }))
  );

  const phase = derivePhase(activeRunStatus);

  const activeRun = useMemo<AgentRun>(() => ({
    runId: selectedRunId,
    sessionId: selectedSessionId,
    messageId: selectedMessageId,
    scope: deriveScope(scope),
    mode,
    status: activeRunStatus,
    phase,
    currentPhase: phase,
    objective: '',
    steps: [],
    toolEvents: [],
    timeline: [],
    pendingActions,
    confirmation: null,
    artifacts: [],
    evidence: [],
    outcome: {},
    recoverable: false,
  }), [
    activeRunStatus,
    mode,
    pendingActions,
    phase,
    scope,
    selectedMessageId,
    selectedRunId,
    selectedSessionId,
  ]);

  return { activeRun };
}
