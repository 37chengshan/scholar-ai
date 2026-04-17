import { useCallback, useState } from 'react';
import * as searchApi from '@/services/searchApi';
import { AuthorPaper, AuthorSearchResult } from '@/services/searchApi';
import { toast } from 'sonner';

export function useAuthorSearch() {
  const [authorResults, setAuthorResults] = useState<AuthorSearchResult[]>([]);
  const [authorLoading, setAuthorLoading] = useState(false);
  const [selectedAuthor, setSelectedAuthor] = useState<AuthorSearchResult | null>(null);
  const [authorPapers, setAuthorPapers] = useState<AuthorPaper[]>([]);
  const [loadingAuthorPapers, setLoadingAuthorPapers] = useState(false);
  const [showAuthorPapersModal, setShowAuthorPapersModal] = useState(false);

  const searchAuthors = useCallback(async (query: string) => {
    if (query.length < 3) {
      setAuthorResults([]);
      return;
    }

    setAuthorLoading(true);
    try {
      const response = await searchApi.searchAuthors(query);
      setAuthorResults(response.data);
    } catch (error: any) {
      toast.error(error?.response?.data?.error?.detail || '作者搜索失败');
      setAuthorResults([]);
    } finally {
      setAuthorLoading(false);
    }
  }, []);

  const openAuthorPapers = useCallback(async (author: AuthorSearchResult) => {
    try {
      setSelectedAuthor(author);
      setLoadingAuthorPapers(true);
      setShowAuthorPapersModal(true);
      const papers = await searchApi.getAuthorPapers(author.authorId, 20, 0);
      setAuthorPapers(papers.data);
    } catch (error: any) {
      toast.error(error?.response?.data?.error?.detail || '获取作者论文失败');
      setShowAuthorPapersModal(false);
    } finally {
      setLoadingAuthorPapers(false);
    }
  }, []);

  return {
    authorResults,
    authorLoading,
    selectedAuthor,
    authorPapers,
    loadingAuthorPapers,
    showAuthorPapersModal,
    setShowAuthorPapersModal,
    searchAuthors,
    openAuthorPapers,
  };
}
