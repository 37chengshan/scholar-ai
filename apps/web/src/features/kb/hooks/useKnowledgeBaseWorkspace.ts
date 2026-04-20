import { useEffect, useMemo, useRef } from 'react';
import { useLocation, useSearchParams } from 'react-router';
import { useKBWorkspaceStore } from '@/features/kb/state/kbWorkspaceStore';
import { useKnowledgeBaseQueries } from '@/features/kb/hooks/useKnowledgeBaseQueries';
import { useKnowledgeBaseSearch } from '@/features/kb/hooks/useKnowledgeBaseSearch';

interface KnowledgeBaseNavigationState {
  importJobId?: string;
  justImported?: boolean;
  paperId?: string;
}

export function useKnowledgeBaseWorkspace() {
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const initializedRef = useRef(false);
  const handledImportSignalRef = useRef<string | null>(null);
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
  const navigationState = (location.state as KnowledgeBaseNavigationState | null) ?? null;
  const importedPaperId = navigationState?.justImported ? navigationState.paperId ?? null : null;

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

  useEffect(() => {
    if (!navigationState?.justImported) {
      return;
    }

    const importSignal = navigationState.importJobId ?? navigationState.paperId ?? `${location.pathname}${location.search}`;

    if (handledImportSignalRef.current === importSignal) {
      return;
    }

    handledImportSignalRef.current = importSignal;
    void queries.refreshAll({ silent: true });
  }, [location.pathname, location.search, navigationState, queries]);

  const syncTab = (tab: string) => {
    setActiveTab(tab);
    setSearchParams({ tab });
  };

  return {
    activeTab,
    isImportDialogOpen,
    importedPaperId,
    searchDraft,
    searchResults,
    queries,
    search,
    setImportDialogOpen,
    refreshAll: queries.refreshAll,
    syncTab,
  };
}
