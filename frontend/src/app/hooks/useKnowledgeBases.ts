/**
 * React hook for fetching knowledge bases with filters
 *
 * Provides:
 * - knowledgeBases: Array of KB objects
 * - total: Total count
 * - loading: Loading state
 * - error: Error message
 * - refetch: Manual refetch function
 * - createKB: Create new KB
 * - deleteKB: Delete KB by ID
 */
import { useState, useEffect, useCallback } from 'react';
import { kbApi, KnowledgeBase, KBListParams } from '@/services/kbApi';

interface UseKnowledgeBasesOptions extends KBListParams {
  autoFetch?: boolean;
}

interface UseKnowledgeBasesResult {
  knowledgeBases: KnowledgeBase[];
  total: number;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
  createKB: (data: any) => Promise<KnowledgeBase>;
  deleteKB: (id: string) => Promise<void>;
}

export function useKnowledgeBases(options: UseKnowledgeBasesOptions = {}): UseKnowledgeBasesResult {
  const { search, category, sortBy = 'updated', limit = 50, offset = 0, autoFetch = true } = options;

  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchKBs = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await kbApi.list({ search, category, sortBy, limit, offset });
      if (response.success && response.data) {
        setKnowledgeBases(response.data.knowledgeBases);
        setTotal(response.data.total);
      } else {
        setError('Failed to fetch knowledge bases');
      }
    } catch (err: any) {
      setError(err.message || 'Network error');
    } finally {
      setLoading(false);
    }
  }, [search, category, sortBy, limit, offset]);

  const createKB = useCallback(async (data: any): Promise<KnowledgeBase> => {
    const response = await kbApi.create(data);
    if (response.success && response.data) {
      setKnowledgeBases(prev => [...prev, response.data]);
      setTotal(prev => prev + 1);
      return response.data;
    }
    throw new Error('Failed to create KB');
  }, []);

  const deleteKB = useCallback(async (id: string): Promise<void> => {
    await kbApi.delete(id);
    setKnowledgeBases(prev => prev.filter(kb => kb.id !== id));
    setTotal(prev => prev - 1);
  }, []);

  useEffect(() => {
    if (autoFetch) {
      fetchKBs();
    }
  }, [autoFetch, fetchKBs]);

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