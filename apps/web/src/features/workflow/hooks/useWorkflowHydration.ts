import { useEffect, useMemo, useRef } from 'react';
import { useLocation } from 'react-router';
import { trackWorkflowEvent } from '@/lib/observability/telemetry';
import { useChatWorkspaceStore } from '@/features/chat/state/chatWorkspaceStore';
import {
  mapAgentRunArtifacts,
  mapAgentRunTimeline,
  mapAgentRunToWorkflowViewModel,
  mapArtifactToUiRenderable,
  mapChatScopeToWorkflowScope,
  mapImportJobToWorkflowCard,
  mapPendingActionsToWorkflowActions,
  mapRunToWorkflowViewModel,
} from '@/features/workflow/adapters/workflowAdapters';
import { resolveNextActions, resolveRecoverableActions } from '@/features/workflow/resolvers/workflowResolvers';
import { workflowActions } from '@/features/workflow/state/workflowActions';
import type { WorkflowArtifact, WorkflowHydratedPayload, WorkflowRun, WorkflowScope } from '@/features/workflow/types';

const SEARCH_IMPORT_STORAGE_KEY = 'search_import_active_job';

function deriveScope(pathname: string, search: string, chatScope: ReturnType<typeof useChatWorkspaceStore.getState>['scope']): WorkflowScope {
  const params = new URLSearchParams(search);

  if (pathname.startsWith('/chat')) {
    if (chatScope.type || chatScope.id) {
      return mapChatScopeToWorkflowScope(chatScope);
    }

    return mapChatScopeToWorkflowScope({
      type: params.get('paperId') ? 'single_paper' : params.get('kbId') ? 'full_kb' : 'general',
      id: params.get('paperId') || params.get('kbId'),
    });
  }

  if (pathname === '/knowledge-bases' || pathname.startsWith('/knowledge-bases/')) {
    const kbId = pathname.startsWith('/knowledge-bases/') ? pathname.split('/')[2] || null : null;
    return {
      type: 'knowledge-base',
      id: kbId,
      title: 'Library Workflow',
      subtitle: kbId ? `Managing import and retrieval for ${kbId}` : 'Library workflow context',
    };
  }

  if (pathname.startsWith('/read/')) {
    const paperId = pathname.split('/')[2] || null;
    return {
      type: 'paper',
      id: paperId,
      title: 'Reading Workflow',
      subtitle: paperId ? `Evidence-linked reading for ${paperId}` : 'Reading workflow context',
    };
  }

  if (pathname.startsWith('/search')) {
    return {
      type: 'global',
      id: null,
      title: 'Discovery Workflow',
      subtitle: 'Search, import, and continue in one flow',
    };
  }

  return {
    type: 'global',
    id: null,
    title: 'Global Workspace',
    subtitle: 'Track pending work and output artifacts',
  };
}

function deriveRun(pathname: string, state: unknown, activeRun: ReturnType<typeof useChatWorkspaceStore.getState>['activeRun']): WorkflowRun | null {
  const locationState = (state || {}) as { importJobId?: string };
  if (locationState.importJobId) {
    return mapRunToWorkflowViewModel({
      id: locationState.importJobId,
      source: 'library-import',
      status: 'running',
      stage: 'import',
      nextAction: 'Monitor import progress',
      scopeType: 'knowledge-base',
    });
  }

  let persisted: string | null = null;
  try {
    persisted = window.sessionStorage.getItem(SEARCH_IMPORT_STORAGE_KEY);
  } catch {
    persisted = null;
  }
  if (persisted) {
    try {
      const parsed = JSON.parse(persisted) as { jobId?: string };
      if (parsed.jobId) {
        return mapImportJobToWorkflowCard({
          jobId: parsed.jobId,
          status: 'running',
          stage: 'import',
        });
      }
    } catch {
      window.sessionStorage.removeItem(SEARCH_IMPORT_STORAGE_KEY);
    }
  }

  if (pathname.startsWith('/chat')) {
    return mapAgentRunToWorkflowViewModel(activeRun);
  }

  return null;
}

function buildArtifacts(
  pathname: string,
  scope: WorkflowScope,
  activeRun: ReturnType<typeof useChatWorkspaceStore.getState>['activeRun']
): WorkflowHydratedPayload['artifacts'] {
  const artifacts: WorkflowArtifact[] = [];

  if (pathname.startsWith('/read/')) {
    artifacts.push(
      mapArtifactToUiRenderable({
        id: 'artifact-note',
        kind: 'note',
        title: 'Reading Notes',
        context: 'Context-linked notes are available in this scope.',
      }),
      mapArtifactToUiRenderable({
        id: 'artifact-citation',
        kind: 'citation',
        title: 'Citation References',
        context: 'Use references for evidence-backed writing.',
      })
    );
  }

  if (pathname.startsWith('/knowledge-bases')) {
    artifacts.push(
      mapArtifactToUiRenderable({
        id: 'artifact-import-report',
        kind: 'import-report',
        title: 'Import Reports',
        context: 'Track import outcomes and unresolved files.',
      })
    );
  }

  if (pathname.startsWith('/chat')) {
    if (activeRun.runId) {
      return mapAgentRunArtifacts(activeRun);
    }

    artifacts.push(
      mapArtifactToUiRenderable({
        id: 'artifact-answer',
        kind: 'answer',
        title: 'Answer Draft',
        context: 'Latest assistant answer in current workspace scope.',
      }),
      mapArtifactToUiRenderable({
        id: 'artifact-session',
        kind: 'session',
        title: 'Session Context',
        context: scope.id ? `Scoped session for ${scope.id}` : 'Global chat session context.',
      })
    );
  }

  return artifacts;
}

function resolveWorkflowPage(pathname: string): 'chat' | 'search' | 'knowledge-base' | 'read' | 'analytics' {
  if (pathname.startsWith('/chat')) {
    return 'chat';
  }
  if (pathname.startsWith('/search')) {
    return 'search';
  }
  if (pathname === '/knowledge-bases' || pathname.startsWith('/knowledge-bases/')) {
    return 'knowledge-base';
  }
  if (pathname.startsWith('/read/')) {
    return 'read';
  }
  return 'analytics';
}

export function useWorkflowHydration(): void {
  const location = useLocation();
  const chatScope = useChatWorkspaceStore((state) => state.scope);
  const activeRun = useChatWorkspaceStore((state) => state.activeRun);
  const lastTelemetrySignature = useRef<string | null>(null);

  const payload = useMemo<WorkflowHydratedPayload>(() => {
    const scope = deriveScope(location.pathname, location.search, chatScope);
    const currentRun = deriveRun(location.pathname, location.state, activeRun);
    const pendingActions = location.pathname.startsWith('/chat')
      ? mapPendingActionsToWorkflowActions(activeRun.pendingActions)
      : resolveNextActions(currentRun);
    const recoverableTasks = location.pathname.startsWith('/chat') && activeRun.recoverable
      ? mapPendingActionsToWorkflowActions(activeRun.pendingActions.filter((action) => action.type === 'retry' || action.type === 'cancel' || action.type === 'resume'))
      : resolveRecoverableActions(currentRun);
    const artifacts = buildArtifacts(location.pathname, scope, activeRun);
    const timeline = location.pathname.startsWith('/chat') && activeRun.runId
      ? mapAgentRunTimeline(activeRun)
      : [
          {
            id: `timeline-${location.pathname}`,
            title: 'Scope Updated',
            description: `Entered ${location.pathname}`,
            at: new Date().toISOString(),
          },
        ];

    return {
      scope,
      currentRun,
      pendingActions,
      recoverableTasks,
      artifacts,
      timeline,
    };
  }, [activeRun, chatScope, location.pathname, location.search, location.state]);

  useEffect(() => {
    workflowActions.hydrate(payload);
  }, [payload]);

  useEffect(() => {
    const run = payload.currentRun;
    const signature = JSON.stringify({
      path: location.pathname,
      runId: run?.id ?? null,
      status: run?.status ?? null,
      stage: run?.stage ?? null,
      updatedAt: run?.updatedAt ?? null,
      pendingActions: payload.pendingActions.length,
      recoverableTasks: payload.recoverableTasks.length,
    });

    if (signature === lastTelemetrySignature.current) {
      return;
    }
    lastTelemetrySignature.current = signature;

    trackWorkflowEvent({
      event: run ? 'workflow_hydrated' : 'workflow_scope_viewed',
      page: resolveWorkflowPage(location.pathname),
      scopeType: payload.scope.type,
      scopeId: payload.scope.id,
      runId: run?.id ?? null,
      traceId: run?.traceId ?? null,
      sessionId: run?.sessionId ?? null,
      messageId: run?.messageId ?? null,
      status: run?.status,
      stage: run?.stage,
      durationMs: run?.durationMs ?? null,
      tokensUsed: run?.tokensUsed,
      cost: run?.cost,
      metadata: {
        pendingActions: payload.pendingActions.length,
        recoverableTasks: payload.recoverableTasks.length,
        artifacts: payload.artifacts.length,
        timelineItems: payload.timeline.length,
      },
    });
  }, [location.pathname, payload]);
}
