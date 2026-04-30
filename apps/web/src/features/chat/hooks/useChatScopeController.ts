import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router';
import { toast } from 'sonner';
import * as papersApi from '@/services/papersApi';
import { kbApi } from '@/services/kbApi';
import type { WorkspaceScope } from '@/features/chat/state/chatWorkspaceStore';
import { parseScopeFromQuery } from './chatScopeQuery';

interface UseChatScopeControllerOptions {
  mode: 'auto' | 'rag' | 'agent';
  isZh: boolean;
  setMode: (mode: 'auto' | 'rag' | 'agent') => void;
  setWorkspaceScope: (scope: WorkspaceScope) => void;
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
}: UseChatScopeControllerOptions) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [scope, setScope] = useState<WorkspaceScope>({ type: null, id: null });
  const [scopeLoading, setScopeLoading] = useState(false);
  const scopeQuerySignature = searchParams.toString();

  const paperId = searchParams.get('paperId');
  const kbId = searchParams.get('kbId');
  const comparePaperIds = useMemo(
    () =>
      (searchParams.get('paper_ids') || '')
        .split(',')
        .map((id) => id.trim())
        .filter(Boolean),
    [scopeQuerySignature],
  );

  useEffect(() => {
    let cancelled = false;

    const applyScope = async () => {
      const parsedScope = parseScopeFromQuery(new URLSearchParams(scopeQuerySignature));

      if (!paperId && !kbId) {
        if (comparePaperIds.length > 0) {
          const compareScope: WorkspaceScope = {
            ...parsedScope,
            title: isZh ? `对比论文集 (${comparePaperIds.length})` : `Comparison set (${comparePaperIds.length})`,
          };
          setScope(compareScope);
          setWorkspaceScope(compareScope);
          setScopeLoading(false);
          return;
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
