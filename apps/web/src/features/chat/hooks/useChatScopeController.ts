import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router';
import { toast } from 'sonner';
import * as papersApi from '@/services/papersApi';
import { kbApi } from '@/services/kbApi';
import type { WorkspaceScope } from '@/features/chat/state/chatWorkspaceStore';
import { parseScopeFromQuery } from './chatScopeQuery';
import type { SessionScopeMetadata } from '@/services/sessionsApi';

interface UseChatScopeControllerOptions {
  mode: 'auto' | 'rag' | 'agent';
  isZh: boolean;
  setMode: (mode: 'auto' | 'rag' | 'agent') => void;
  setWorkspaceScope: (scope: WorkspaceScope) => void;
  sessionScopeMetadata?: SessionScopeMetadata | null;
}

function isPaperEvidenceReady(paper: {
  evidenceReady?: boolean | null;
  chunkCount?: number;
}): boolean {
  if (typeof paper.evidenceReady === 'boolean') {
    return paper.evidenceReady;
  }
  return (paper.chunkCount ?? 0) >= 2;
}

const SCOPE_VALIDATION_TIMEOUT_MS = 15_000;

async function withTimeout<T>(promise: Promise<T>, timeoutMs: number): Promise<T> {
  return await Promise.race([
    promise,
    new Promise<never>((_, reject) => {
      setTimeout(() => reject(new Error(`scope_validation_timeout_${timeoutMs}`)), timeoutMs);
    }),
  ]);
}

export function useChatScopeController({
  mode,
  isZh,
  setMode,
  setWorkspaceScope,
  sessionScopeMetadata,
}: UseChatScopeControllerOptions) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [scope, setScope] = useState<WorkspaceScope>({ type: null, id: null });
  const [scopeLoading, setScopeLoading] = useState(false);
  const effectiveScopeParams = useMemo(() => {
    const next = new URLSearchParams(searchParams);
    const hasExplicitScope = Boolean(
      next.get('paperId') || next.get('kbId') || next.get('paper_ids'),
    );

    if (hasExplicitScope || !sessionScopeMetadata?.scopeType) {
      return next;
    }

    if (sessionScopeMetadata.scopeType === 'single_paper' && sessionScopeMetadata.paperId) {
      next.set('paperId', sessionScopeMetadata.paperId);
      return next;
    }

    if (sessionScopeMetadata.scopeType === 'full_kb' && sessionScopeMetadata.kbId) {
      next.set('kbId', sessionScopeMetadata.kbId);
      return next;
    }

    if (
      sessionScopeMetadata.scopeType === 'compare'
      && Array.isArray(sessionScopeMetadata.paperIds)
      && sessionScopeMetadata.paperIds.length > 0
    ) {
      next.set('paper_ids', sessionScopeMetadata.paperIds.join(','));
    }

    return next;
  }, [searchParams, sessionScopeMetadata]);

  const scopeQuerySignature = effectiveScopeParams.toString();

  const paperId = effectiveScopeParams.get('paperId');
  const kbId = effectiveScopeParams.get('kbId');
  const comparePaperIds = useMemo(
    () =>
      (effectiveScopeParams.get('paper_ids') || '')
        .split(',')
        .map((id) => id.trim())
        .filter(Boolean),
    [effectiveScopeParams, scopeQuerySignature],
  );

  useEffect(() => {
    let cancelled = false;

    const applyScope = async () => {
      const parsedScope = parseScopeFromQuery(new URLSearchParams(scopeQuerySignature));

      if (!paperId && !kbId) {
        if (comparePaperIds.length > 0) {
          setScopeLoading(true);
          try {
            const results = await withTimeout(
              Promise.allSettled(comparePaperIds.map((id) => papersApi.get(id))),
              SCOPE_VALIDATION_TIMEOUT_MS,
            );
            if (cancelled) {
              return;
            }
            const papers = results
              .filter((result): result is PromiseFulfilledResult<Awaited<ReturnType<typeof papersApi.get>>> => result.status === 'fulfilled')
              .map((result) => result.value);
            const unavailable = papers.filter((paper) => !isPaperEvidenceReady(paper));
            const missingCount = comparePaperIds.length - papers.length;
            if (missingCount > 0 || unavailable.length > 0) {
              const badTitle = unavailable[0]?.title;
              const reason = badTitle
                ? (isZh ? `《${badTitle}》尚未完成证据索引，暂不能用于对比或对比问答。` : `"${badTitle}" is not evidence-ready for comparison yet.`)
                : (isZh ? '部分论文尚未完成证据索引，暂不能用于对比或对比问答。' : 'Some papers are not evidence-ready for comparison yet.');
              const errorScope: WorkspaceScope = {
                type: 'error',
                id: comparePaperIds.join(','),
                title: isZh ? `对比论文集 (${comparePaperIds.length})` : `Comparison set (${comparePaperIds.length})`,
                errorMessage: reason,
              };
              setScope(errorScope);
              setWorkspaceScope(errorScope);
              return;
            }

            const compareScope: WorkspaceScope = {
              ...parsedScope,
              type: 'compare',
              title: isZh ? `对比论文集 (${comparePaperIds.length})` : `Comparison set (${comparePaperIds.length})`,
            };
            setScope(compareScope);
            setWorkspaceScope(compareScope);
            return;
          } catch {
            if (cancelled) {
              return;
            }
            const errorScope: WorkspaceScope = {
              type: 'error',
              id: comparePaperIds.join(','),
              title: isZh ? `对比论文集 (${comparePaperIds.length})` : `Comparison set (${comparePaperIds.length})`,
              errorMessage: isZh ? '对比论文验证失败' : 'Failed to validate comparison papers',
            };
            setScope(errorScope);
            setWorkspaceScope(errorScope);
            return;
          } finally {
            if (!cancelled) {
              setScopeLoading(false);
            }
          }
        }
        setScope(parsedScope);
        setWorkspaceScope(parsedScope);
        setScopeLoading(false);
        return;
      }

      if (parsedScope.type === 'error') {
        setScope(parsedScope);
        setWorkspaceScope(parsedScope);
        setScopeLoading(false);
        return;
      }

      setScopeLoading(true);

      try {
        if (paperId) {
          let nextScope: WorkspaceScope;
          try {
            const paper = await withTimeout(papersApi.get(paperId), SCOPE_VALIDATION_TIMEOUT_MS);
            nextScope = {
              type: 'single_paper',
              id: paperId,
              title: paper.title || (isZh ? '未知论文' : 'Unknown paper'),
            };
          } catch {
            nextScope = {
              type: 'single_paper',
              id: paperId,
              title: isZh ? '单论文对话' : 'Single-paper chat',
            };
          }
          if (cancelled) {
            return;
          }

          setScope(nextScope);
          setWorkspaceScope(nextScope);
          return;
        }

        if (kbId) {
          let nextScope: WorkspaceScope;
          try {
            const knowledgeBase = await withTimeout(kbApi.get(kbId), SCOPE_VALIDATION_TIMEOUT_MS);
            nextScope = {
              type: 'full_kb',
              id: kbId,
              title: knowledgeBase.name,
            };
          } catch {
            nextScope = {
              type: 'full_kb',
              id: kbId,
              title: isZh ? '知识库对话' : 'Knowledge-base chat',
            };
          }
          if (cancelled) {
            return;
          }

          setScope(nextScope);
          setWorkspaceScope(nextScope);
          return;
        }
      } catch {
        if (cancelled) {
          return;
        }

        const nextScope: WorkspaceScope = {
          type: 'error',
          id: paperId || kbId,
          errorMessage: isZh ? '作用域验证失败' : 'Failed to validate scope',
        };

        setScope(nextScope);
        setWorkspaceScope(nextScope);
      } finally {
        if (!cancelled) {
          setScopeLoading(false);
        }
      }
    };

    void applyScope();

    return () => {
      cancelled = true;
    };
  }, [comparePaperIds, isZh, kbId, paperId, scopeQuerySignature, setWorkspaceScope]);

  useEffect(() => {
    if (scope.type === 'single_paper' || scope.type === 'full_kb' || comparePaperIds.length > 0) {
      if (mode === 'auto') {
        setMode('rag');
      }
      return;
    }

    setMode('auto');
  }, [comparePaperIds.length, mode, scope.type, setMode]);

  const handleExitScope = useCallback(() => {
    const nextParams = new URLSearchParams(searchParams);
    nextParams.delete('paperId');
    nextParams.delete('kbId');
    nextParams.delete('paper_ids');
    setSearchParams(nextParams);

    const nextScope: WorkspaceScope = { type: null, id: null };
    setScope(nextScope);
    setWorkspaceScope(nextScope);
    toast.info(isZh ? '已退出作用域模式' : 'Scope cleared');
  }, [isZh, searchParams, setSearchParams, setWorkspaceScope]);

  return {
    scope,
    scopeLoading,
    paperId,
    kbId,
    handleExitScope,
  };
}
