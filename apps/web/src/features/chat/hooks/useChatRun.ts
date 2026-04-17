import { useMemo } from 'react';
import type { AgentRun, RunScope, RunStatus } from '@/features/chat/types/run';
import { useChatWorkspaceStore } from '@/features/chat/state/chatWorkspaceStore';

function deriveScope(scope: { paperId: string | null; kbId: string | null }): RunScope {
  if (scope.paperId) {
    return 'single_paper';
  }
  if (scope.kbId) {
    return 'full_kb';
  }
  return 'general';
}

function derivePhase(status: RunStatus): string {
  if (status === 'running') {
    return 'executing';
  }
  if (status === 'waiting_confirmation') {
    return 'waiting_confirmation';
  }
  if (status === 'completed') {
    return 'done';
  }
  if (status === 'failed') {
    return 'error';
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
  } = useChatWorkspaceStore();

  const activeRun = useMemo<AgentRun>(() => ({
    runId: selectedRunId,
    sessionId: selectedSessionId,
    messageId: selectedMessageId,
    scope: deriveScope(scope),
    mode,
    status: activeRunStatus,
    currentPhase: derivePhase(activeRunStatus),
    timeline: [],
    pendingActions,
    artifacts: [],
    outcome: {},
  }), [
    activeRunStatus,
    mode,
    pendingActions,
    scope,
    selectedMessageId,
    selectedRunId,
    selectedSessionId,
  ]);

  return { activeRun };
}
