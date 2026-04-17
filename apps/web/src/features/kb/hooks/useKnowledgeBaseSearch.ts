import { useCallback, useState } from 'react';
import { kbApi, KBSearchResult } from '@/services/kbApi';
import { toast } from 'sonner';

export function useKnowledgeBaseSearch(kbId: string | undefined) {
  const [searchDraft, setSearchDraft] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState<KBSearchResult[] | null>(null);

  const search = useCallback(async (query: string) => {
    if (!kbId || !query.trim()) {
      return;
    }

    setIsSearching(true);
    try {
      const response = await kbApi.search(kbId, query);
      setResults(response.results || []);
    } catch (error: any) {
      toast.error(error?.message || '搜索失败');
    } finally {
      setIsSearching(false);
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
