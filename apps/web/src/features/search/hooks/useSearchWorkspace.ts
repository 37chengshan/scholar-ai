import { useEffect, useMemo } from 'react';
import { useUrlState } from '@/hooks/useUrlState';
import { useSearchWorkspaceStore } from '@/features/search/state/searchWorkspaceStore';

export function useSearchWorkspace() {
  const [activeSourceFromUrl, setActiveSourceFromUrl] = useUrlState<string>('source', 'all');
  const [sortByFromUrl, setSortByFromUrl] = useUrlState<'relevance' | 'date'>('sort', 'relevance');
  const [queryFromUrl] = useUrlState<string>('q', '');
  const [pageFromUrl] = useUrlState<number>('page', 0);

  const {
    activeSource,
    sortBy,
    selectedAuthorId,
    pendingImportPaper,
    selectedKnowledgeBaseId,
    setActiveSource,
    setSortBy,
    setSelectedAuthorId,
    setPendingImportPaper,
    setSelectedKnowledgeBaseId,
  } = useSearchWorkspaceStore();

  useEffect(() => {
    setActiveSource(activeSourceFromUrl);
  }, [activeSourceFromUrl, setActiveSource]);

  useEffect(() => {
    setSortBy(sortByFromUrl);
  }, [setSortBy, sortByFromUrl]);

  const updateActiveSource = (source: string) => {
    setActiveSourceFromUrl(source);
    setActiveSource(source);
  };

  const updateSortBy = (nextSort: 'relevance' | 'date') => {
    setSortByFromUrl(nextSort);
    setSortBy(nextSort);
  };

  return useMemo(() => ({
    activeSource,
    sortBy,
    queryFromUrl,
    pageFromUrl,
    selectedAuthorId,
    pendingImportPaper,
    selectedKnowledgeBaseId,
    updateActiveSource,
    updateSortBy,
    setSelectedAuthorId,
    setPendingImportPaper,
    setSelectedKnowledgeBaseId,
  }), [
    activeSource,
    sortBy,
    queryFromUrl,
    pageFromUrl,
    selectedAuthorId,
    pendingImportPaper,
    selectedKnowledgeBaseId,
    setSelectedAuthorId,
    setPendingImportPaper,
    setSelectedKnowledgeBaseId,
  ]);
}
