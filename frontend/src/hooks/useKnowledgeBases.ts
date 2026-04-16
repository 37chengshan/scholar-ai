/**
 * useKnowledgeBases Hook
 *
 * Provides knowledge base list data with search, category filter, and sorting.
 *
 * Features:
 * - Auto-refresh on mount
 * - Real API integration via kbApi
 * - Create/delete operations
 */
import { useState, useEffect, useCallback } from 'react';
import { kbApi, KnowledgeBase, KBListParams, KBCreateData } from '@/services/kbApi';

interface UseKnowledgeBasesParams extends KBListParams {
  autoFetch?: boolean;
}

interface UseKnowledgeBasesReturn {
  knowledgeBases: KnowledgeBase[];
  total: number;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
  createKB: (data: KBCreateData) => Promise<KnowledgeBase>;
  deleteKB: (id: string) => Promise<boolean>;
}

export function useKnowledgeBases(params?: UseKnowledgeBasesParams): UseKnowledgeBasesReturn {
  const {
    search,
    category,
    sortBy = 'updated',
    limit = 50,
    offset = 0,
    autoFetch = true,
  } = params || {};

  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchKBs = useCallback(async (): Promise<void> => {
    setLoading(true);
    setError(null);

    try {
      const response = await kbApi.list({ search, category, sortBy, limit, offset });
      setKnowledgeBases(response.knowledgeBases || []);
      setTotal(response.total || 0);
    } catch (err: any) {
      setError(err.message || '网络错误');
      setKnowledgeBases([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [search, category, sortBy, limit, offset]);

  useEffect(() => {
    if (autoFetch) {
      void fetchKBs();
    }
  }, [autoFetch, fetchKBs]);

  const createKB = useCallback(async (data: KBCreateData): Promise<KnowledgeBase> => {
    try {
      const created = await kbApi.create(data);
      setKnowledgeBases(prev => [...prev, created]);
      setTotal(prev => prev + 1);
      return created;
    } catch (err: any) {
      console.error('Create KB failed:', err);
      throw err;
    }
  }, []);

  const deleteKB = useCallback(async (id: string) => {
    try {
      const response = await kbApi.delete(id);
      if (!response.deleted) {
        return false;
      }

      setKnowledgeBases(prev => prev.filter(kb => kb.id !== id));
      setTotal(prev => Math.max(0, prev - 1));
      return true;
    } catch (err: any) {
      console.error('Delete KB failed:', err);
      return false;
    }
  }, []);

  return {
    knowledgeBases,
    total,
    loading,
    error,
    refetch: fetchKBs,
    createKB,
    deleteKB,
  };
}

export default useKnowledgeBases;