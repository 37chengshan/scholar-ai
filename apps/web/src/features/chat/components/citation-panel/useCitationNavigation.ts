/**
 * useCitationNavigation - Handles citation click navigation with URL allowlist
 *
 * Security: citation_jump_url is validated against an allowlist before navigation.
 * Only same-origin /read routes are permitted.
 */

import { useCallback } from 'react';
import { useNavigate } from 'react-router';
import type { CitationItem } from '@/features/chat/components/workspaceTypes';

/**
 * Validates citation_jump_url against an allowlist.
 * Only allows same-origin /read?paperId=xxx&page=yyy format.
 */
export function isAllowedCitationUrl(url: string | undefined): boolean {
  if (!url) return false;

  try {
    const parsed = new URL(url, window.location.origin);

    // Must be same-origin
    if (parsed.origin !== window.location.origin) return false;

    // Must start with /read
    if (!parsed.pathname.startsWith('/read')) return false;

    // No protocol-relative schemes
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') return false;

    return true;
  } catch {
    // Invalid URL
    return false;
  }
}

interface UseCitationNavigationOptions {
  onCitationClick?: (citation: CitationItem) => void;
}

interface UseCitationNavigationResult {
  navigateToCitation: (citation: CitationItem) => void;
}

export function useCitationNavigation({
  onCitationClick,
}: UseCitationNavigationOptions = {}): UseCitationNavigationResult {
  const navigate = useNavigate();

  const navigateToCitation = useCallback((citation: CitationItem) => {
    // Notify parent if provided
    onCitationClick?.(citation);

    // Try allowlisted jump URL first
    if (isAllowedCitationUrl(citation.citation_jump_url)) {
      navigate(citation.citation_jump_url!);
      return;
    }

    // Fallback: construct navigation from citation data
    const paperId = citation.paper_id;
    const page = citation.page_num || citation.page || 1;
    const sourceChunkId = citation.source_chunk_id || citation.source_id || citation.chunk_id;

    if (!paperId) return;

    const sourceQuery = sourceChunkId
      ? `&source=chat&source_id=${encodeURIComponent(sourceChunkId)}`
      : '';
    navigate(`/read/${paperId}?page=${page}${sourceQuery}`);
  }, [navigate, onCitationClick]);

  return { navigateToCitation };
}
