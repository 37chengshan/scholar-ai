import { useCallback, useEffect, useState } from 'react';
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

export function useChatScopeController({
  mode,
  isZh,
  setMode,
  setWorkspaceScope,
}: UseChatScopeControllerOptions) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [scope, setScope] = useState<WorkspaceScope>({ type: null, id: null });
  const [scopeLoading, setScopeLoading] = useState(false);

  const paperId = searchParams.get('paperId');
  const kbId = searchParams.get('kbId');

  useEffect(() => {
    let cancelled = false;

    const applyScope = async () => {
      const parsedScope = parseScopeFromQuery(searchParams);

      if (!paperId && !kbId) {
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
          const paper = await papersApi.get(paperId);
          if (cancelled) {
            return;
          }

          const nextScope: WorkspaceScope = {
            type: 'single_paper',
            id: paperId,
            title: paper.title || (isZh ? '未知论文' : 'Unknown paper'),
          };

          setScope(nextScope);
          setWorkspaceScope(nextScope);
          return;
        }

        if (kbId) {
          const knowledgeBase = await kbApi.get(kbId);
          if (cancelled) {
            return;
          }

          const nextScope: WorkspaceScope = {
            type: 'full_kb',
            id: kbId,
            title: knowledgeBase.name,
          };

          setScope(nextScope);
          setWorkspaceScope(nextScope);
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
  }, [isZh, kbId, paperId, searchParams, setWorkspaceScope]);

  useEffect(() => {
    if (scope.type === 'single_paper' || scope.type === 'full_kb') {
      if (mode === 'auto') {
        setMode('rag');
      }
      return;
    }

    setMode('auto');
  }, [mode, scope.type, setMode]);

  const handleExitScope = useCallback(() => {
    const nextParams = new URLSearchParams(searchParams);
    nextParams.delete('paperId');
    nextParams.delete('kbId');
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