import { useEffect, useMemo, useRef } from 'react';
import { useSearchParams } from 'react-router';
import { useKBWorkspaceStore } from '@/features/kb/state/kbWorkspaceStore';
import { useKnowledgeBaseQueries } from '@/features/kb/hooks/useKnowledgeBaseQueries';
import { useKnowledgeBaseSearch } from '@/features/kb/hooks/useKnowledgeBaseSearch';

export function useKnowledgeBaseWorkspace() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initializedRef = useRef(false);
  const {
    activeTab: storeTab,
    isImportDialogOpen,
    searchDraft,
    searchResults,
    setActiveTab,
    setImportDialogOpen,
    setSearchDraft,
    setSearchResults,
  } = useKBWorkspaceStore();
  const queries = useKnowledgeBaseQueries();
  const search = useKnowledgeBaseSearch(queries.kbId);

  const urlTab = searchParams.get('tab');
  const activeTab = useMemo(() => urlTab ?? storeTab, [storeTab, urlTab]);

  useEffect(() => {
    if (!initializedRef.current && !urlTab && storeTab !== 'papers') {
      setActiveTab('papers');
    }
    initializedRef.current = true;
  }, [setActiveTab, storeTab, urlTab]);

  useEffect(() => {
    if (activeTab !== storeTab) {
      setActiveTab(activeTab);
    }
  }, [activeTab, setActiveTab, storeTab]);

  useEffect(() => {
    setSearchDraft(search.searchDraft);
  }, [search.searchDraft, setSearchDraft]);

  useEffect(() => {
    setSearchResults(search.results || []);
  }, [search.results, setSearchResults]);

  const syncTab = (tab: string) => {
    setActiveTab(tab);
    setSearchParams({ tab });
  };

  return {
    activeTab,
    isImportDialogOpen,
    searchDraft,
    searchResults,
    queries,
    search,
    setImportDialogOpen,
    refreshAll: queries.refreshAll,
    syncTab,
  };
}
