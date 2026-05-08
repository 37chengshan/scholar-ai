import { useEffect, useMemo, useRef } from 'react';
import { useLocation } from 'react-router';
import { trackWorkflowEvent } from '@/lib/observability/telemetry';
import { useChatWorkspaceStore } from '@/features/chat/state/chatWorkspaceStore';
import { matchesPersistedChatHandoff, readPersistedChatHandoff } from '@/features/chat/chatHandoff';
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
      title: '知识库工作区',
      subtitle: kbId ? `围绕知识库 ${kbId} 管理导入、检索与综述` : '围绕知识库管理导入、检索与综述',
    };
  }

  if (pathname.startsWith('/read/')) {
    const paperId = pathname.split('/')[2] || null;
    return {
      type: 'paper',
      id: paperId,
      title: '阅读工作区',
      subtitle: paperId ? `围绕论文 ${paperId} 继续阅读、标注与记笔记` : '围绕单篇论文继续阅读、标注与记笔记',
    };
  }

  if (pathname.startsWith('/search')) {
    return {
      type: 'global',
      id: null,
      title: '检索工作区',
      subtitle: '在同一条链路里完成检索、导入与继续研究',
    };
  }

  return {
    type: 'global',
    id: null,
    title: '研究工作区',
    subtitle: '在同一处追踪当前问题、证据与下一步动作',
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

function derivePersistedHandoff(pathname: string, search: string) {
  if (!pathname.startsWith('/chat')) {
    return null;
  }

  const persisted = readPersistedChatHandoff();
  return matchesPersistedChatHandoff(search, persisted) ? persisted : null;
}

function buildHandoffRun(
  handoff: NonNullable<ReturnType<typeof derivePersistedHandoff>>,
  scope: WorkflowScope,
): WorkflowRun {
  const evidenceCount = handoff.handoff.evidence?.length || 0;

  return {
    id: `handoff:${scope.id || handoff.handoff.origin}`,
    source: 'chat',
    status: 'waiting',
    stage: 'ready_to_continue',
    error: null,
    nextAction: evidenceCount > 0
      ? `检查预填问题，并基于 ${evidenceCount} 条证据继续追问。`
      : '检查预填问题并继续提问。',
    updatedAt: handoff.savedAt,
    scopeType: scope.type,
    scopeId: scope.id,
  };
}

function buildHandoffPendingActions(handoff: NonNullable<ReturnType<typeof derivePersistedHandoff>>) {
  const actions: WorkflowHydratedPayload['pendingActions'] = [
    {
      id: 'handoff-continue',
      label: '继续提问',
      description: '输入框里已经准备好可继续发送的问题。',
      intent: 'primary' as const,
      kind: 'primary' as const,
      action: 'open' as const,
    },
  ];

  if (handoff.handoff.returnTo) {
    actions.push({
      id: 'handoff-return',
      label: '返回来源页面',
      description: `检查完预填问题后，回到 ${handoff.handoff.origin} 继续。`,
      intent: 'primary',
      kind: 'primary',
      action: 'open' as const,
      payload: {
        href: handoff.handoff.returnTo,
      },
    });
  }

  return actions;
}

function buildArtifacts(
  pathname: string,
  scope: WorkflowScope,
  activeRun: ReturnType<typeof useChatWorkspaceStore.getState>['activeRun'],
  handoff: ReturnType<typeof derivePersistedHandoff>,
): WorkflowHydratedPayload['artifacts'] {
  const artifacts: WorkflowArtifact[] = [];

  if (pathname.startsWith('/read/')) {
    artifacts.push(
      mapArtifactToUiRenderable({
        id: 'artifact-note',
        kind: 'note',
        title: '阅读笔记',
        context: '当前范围内已有可继续编辑的阅读笔记。',
      }),
      mapArtifactToUiRenderable({
        id: 'artifact-citation',
        kind: 'citation',
        title: '引文引用',
        context: '可直接引用当前范围内的证据来源。',
      })
    );
  }

  if (pathname.startsWith('/knowledge-bases')) {
    artifacts.push(
      mapArtifactToUiRenderable({
        id: 'artifact-import-report',
        kind: 'import-report',
        title: '导入记录',
        context: '查看导入结果与仍待处理的文件。',
      })
    );
  }

  if (pathname.startsWith('/chat')) {
    if (activeRun.runId) {
      return mapAgentRunArtifacts(activeRun);
    }

    if (handoff) {
      const evidenceCount = handoff.handoff.evidence?.length || 0;
      artifacts.push(
        mapArtifactToUiRenderable({
          id: 'artifact-handoff',
          kind: 'session',
          title: '已准备好的追问',
          context: handoff.handoff.promptDraft,
          payload: {
            origin: handoff.handoff.origin,
            returnTo: handoff.handoff.returnTo || null,
          },
        }),
      );

      if (evidenceCount > 0) {
        artifacts.push(
          mapArtifactToUiRenderable({
            id: 'artifact-handoff-evidence',
            kind: 'citation',
            title: `已带入证据（${evidenceCount}）`,
            context: '这些证据引用已从上一个页面带入当前对话。',
            payload: {
              evidence: handoff.handoff.evidence,
            },
          }),
        );
      }
    }

    artifacts.push(
      mapArtifactToUiRenderable({
        id: 'artifact-answer',
        kind: 'answer',
        title: '当前回答',
        context: '当前范围里的最近一次助手回答。',
      }),
      mapArtifactToUiRenderable({
        id: 'artifact-session',
        kind: 'session',
        title: '会话上下文',
        context: scope.id ? `当前会话已绑定到 ${scope.id}` : '当前会话在全局范围内继续。',
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
    const persistedHandoff = derivePersistedHandoff(location.pathname, location.search);
    const baseRun = deriveRun(location.pathname, location.state, activeRun);
    const currentRun = baseRun || (persistedHandoff ? buildHandoffRun(persistedHandoff, scope) : null);
    const pendingActions = location.pathname.startsWith('/chat')
      ? activeRun.runId
        ? mapPendingActionsToWorkflowActions(activeRun.pendingActions)
        : persistedHandoff
          ? buildHandoffPendingActions(persistedHandoff)
          : resolveNextActions(currentRun)
      : resolveNextActions(currentRun);
    const recoverableTasks = location.pathname.startsWith('/chat') && activeRun.recoverable
      ? mapPendingActionsToWorkflowActions(activeRun.pendingActions.filter((action) => action.type === 'retry' || action.type === 'cancel' || action.type === 'resume'))
      : resolveRecoverableActions(currentRun);
    const artifacts = buildArtifacts(location.pathname, scope, activeRun, persistedHandoff);
    const timeline = location.pathname.startsWith('/chat') && activeRun.runId
      ? mapAgentRunTimeline(activeRun)
      : persistedHandoff
        ? [
            {
              id: `timeline-handoff-${persistedHandoff.savedAt}`,
              title: '已恢复追问上下文',
              description: `已把 ${persistedHandoff.handoff.origin} 的上下文带回当前对话。`,
              at: persistedHandoff.savedAt,
              status: 'info' as const,
            },
          ]
      : [
          {
            id: `timeline-${location.pathname}`,
            title: '范围已更新',
            description: `已进入 ${location.pathname}`,
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
