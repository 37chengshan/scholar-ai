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
import { kbApi, KnowledgeBase, KBListParams } from '@/services/kbApi';

interface UseKnowledgeBasesParams {
  search?: string;
  category?: string;
  sortBy?: 'updated' | 'papers' | 'name';
}

interface UseKnowledgeBasesReturn {
  knowledgeBases: KnowledgeBase[];
  loading: boolean;
  error: string | null;
  refetch: () => void;
  createKB: (data: { name: string; description?: string; category?: string }) => Promise<boolean>;
  deleteKB: (id: string) => Promise<boolean>;
}

export function useKnowledgeBases(params?: UseKnowledgeBasesParams): UseKnowledgeBasesReturn {
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchKBs = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await kbApi.list({
        search: params?.search,
        category: params?.category,
        sortBy: params?.sortBy || 'updated',
      });

      if (response.success && response.data) {
        setKnowledgeBases(response.data.knowledgeBases || []);
      } else {
        setError('获取知识库列表失败');
      }
    } catch (err: any) {
      setError(err.message || '网络错误');
    } finally {
      setLoading(false);
    }
  }, [params?.search, params?.category, params?.sortBy]);

  useEffect(() => {
    fetchKBs();
  }, [fetchKBs]);

  const createKB = useCallback(async (data: { name: string; description?: string; category?: string }) => {
    try {
      const response = await kbApi.create(data);
      if (response.success) {
        fetchKBs(); // Refresh list
        return true;
      }
      return false;
    } catch (err: any) {
      console.error('Create KB failed:', err);
      return false;
    }
  }, [fetchKBs]);

  const deleteKB = useCallback(async (id: string) => {
    try {
      const response = await kbApi.delete(id);
      if (response.success) {
        fetchKBs(); // Refresh list
        return true;
      }
      return false;
    } catch (err: any) {
      console.error('Delete KB failed:', err);
      return false;
    }
  }, [fetchKBs]);

  return {
    knowledgeBases,
    loading,
    error,
    refetch: fetchKBs,
    createKB,
    deleteKB,
  };
}

export default useKnowledgeBases;