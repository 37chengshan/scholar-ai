import { useEffect, useMemo } from 'react';
import { useLocation } from 'react-router';
import { mapArtifactToUiRenderable, mapImportJobToWorkflowCard, mapRunToWorkflowViewModel } from '@/features/workflow/adapters/workflowAdapters';
import { resolveNextActions, resolveRecoverableActions } from '@/features/workflow/resolvers/workflowResolvers';
import { workflowActions } from '@/features/workflow/state/workflowActions';
import type { WorkflowArtifact, WorkflowHydratedPayload, WorkflowRun, WorkflowScope } from '@/features/workflow/types';

const SEARCH_IMPORT_STORAGE_KEY = 'search_import_active_job';

function deriveScope(pathname: string, search: string): WorkflowScope {
  const params = new URLSearchParams(search);

  if (pathname.startsWith('/chat')) {
    const paperId = params.get('paperId');
    const kbId = params.get('kbId');
    if (paperId) {
      return {
        type: 'paper',
        id: paperId,
        title: 'Paper Scope',
        subtitle: `Focused QA for paper ${paperId}`,
      };
    }
    if (kbId) {
      return {
        type: 'knowledge-base',
        id: kbId,
        title: 'Library Scope',
        subtitle: `Full KB reasoning for ${kbId}`,
      };
    }
    return {
      type: 'global',
      id: null,
      title: 'Global Workspace',
      subtitle: 'Cross-library research workflow',
    };
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

function deriveRun(pathname: string, state: unknown): WorkflowRun | null {
  const locationState = (state || {}) as { importJobId?: string };
  if (locationState.importJobId) {
    return mapRunToWorkflowViewModel({
      id: locationState.importJobId,
      source: 'library-import',
      status: 'running',
      stage: 'import',
      nextAction: 'Monitor import progress',
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
    return mapRunToWorkflowViewModel({
      id: 'chat-active-run',
      source: 'chat',
      status: 'running',
      stage: 'reasoning',
      nextAction: 'Review evidence and confirm output',
    });
  }

  return null;
}

function buildArtifacts(pathname: string, scope: WorkflowScope): WorkflowHydratedPayload['artifacts'] {
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

export function useWorkflowHydration(): void {
  const location = useLocation();

  const payload = useMemo<WorkflowHydratedPayload>(() => {
    const scope = deriveScope(location.pathname, location.search);
    const currentRun = deriveRun(location.pathname, location.state);
    const pendingActions = resolveNextActions(currentRun);
    const recoverableTasks = resolveRecoverableActions(currentRun);
    const artifacts = buildArtifacts(location.pathname, scope);

    return {
      scope,
      currentRun,
      pendingActions,
      recoverableTasks,
      artifacts,
      timeline: [
        {
          id: `timeline-${location.pathname}`,
          title: 'Scope Updated',
          description: `Entered ${location.pathname}`,
          at: new Date().toISOString(),
        },
      ],
    };
  }, [location.pathname, location.search, location.state]);

  useEffect(() => {
    workflowActions.hydrate(payload);
  }, [payload]);
}
