/**
 * usePageNavigation Hook
 *
 * Manages page navigation, zoom, and URL sync.
 */

import { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router';
import { toast } from 'sonner';

import * as papersApi from '@/services/papersApi';

export function usePageNavigation(
  id: string | undefined,
  isZh: boolean,
) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState<number | null>(null);
  const [scale, setScale] = useState(1.0);
  const [pageInputValue, setPageInputValue] = useState('1');

  const clampPage = useCallback(
    (page: number) => {
      const upper = totalPages || Number.MAX_SAFE_INTEGER;
      return Math.max(1, Math.min(page, upper));
    },
    [totalPages],
  );

  // Sync page from URL
  useEffect(() => {
    const targetPage = searchParams.get('page');
    if (targetPage) {
      const page = parseInt(targetPage, 10);
      if (!isNaN(page) && page >= 1) {
        setCurrentPage(clampPage(page));
      }
    }
  }, [clampPage, searchParams]);

  // Sync page input
  useEffect(() => {
    setPageInputValue(String(currentPage));
  }, [currentPage]);

  const goToPage = useCallback(
    async (
      page: number,
      _reason:
        | 'toolbar'
        | 'thumbnail'
        | 'section'
        | 'citation'
        | 'annotation'
        | 'url' = 'toolbar',
    ) => {
      const nextPage = clampPage(page);
      setCurrentPage(nextPage);
      setPageInputValue(String(nextPage));

      const nextParams = new URLSearchParams(searchParams);
      nextParams.set('page', String(nextPage));
      nextParams.set('source', nextParams.get('source') || 'read');
      setSearchParams(nextParams, { replace: true });

      if (!id) return;
      try {
        await papersApi.saveReadingProgress(id, nextPage);
      } catch {
        toast.warning(
          isZh ? '阅读进度保存失败' : 'Failed to save reading progress',
        );
      }
    },
    [clampPage, id, isZh, searchParams, setSearchParams],
  );

  const handleNumPagesChange = useCallback((numPages: number) => {
    setTotalPages(numPages);
    setCurrentPage((previous) => Math.min(previous, numPages));
  }, []);

  return {
    currentPage,
    setCurrentPage,
    totalPages,
    scale,
    setScale,
    pageInputValue,
    setPageInputValue,
    clampPage,
    goToPage,
    handleNumPagesChange,
  };
}
