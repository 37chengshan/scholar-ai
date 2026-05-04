import { useCallback, useEffect, useRef, useState } from 'react';
import { kbApi, KBSearchResult } from '@/services/kbApi';
import { toast } from 'sonner';

export function useKnowledgeBaseSearch(kbId: string | undefined) {
  const [searchDraft, setSearchDraft] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState<KBSearchResult[] | null>(null);
  const requestIdRef = useRef(0);

  useEffect(() => {
    requestIdRef.current += 1;
    setSearchDraft('');
    setResults(null);
    setIsSearching(false);
  }, [kbId]);

  const search = useCallback(async (query: string) => {
    if (!kbId || !query.trim()) {
      setResults(null);
      return;
    }

    const requestId = ++requestIdRef.current;
    setIsSearching(true);
    try {
      const response = await kbApi.search(kbId, query);
      if (requestId === requestIdRef.current) {
        setResults(response.results || []);
      }
    } catch (error: any) {
      if (requestId === requestIdRef.current) {
        toast.error(error?.message || '搜索失败');
      }
    } finally {
      if (requestId === requestIdRef.current) {
        setIsSearching(false);
      }
    }
  }, [kbId]);

  const clearResults = useCallback(() => {
    setResults(null);
  }, []);

  return {
    searchDraft,
    setSearchDraft,
    isSearching,
    results,
    search,
    clearResults,
  };
}
