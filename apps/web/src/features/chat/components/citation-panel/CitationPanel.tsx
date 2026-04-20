import { CitationsPanel } from '@/app/components/CitationsPanel';
import type { CitationItem } from '@/features/chat/components/workspaceTypes';

interface CitationPanelProps {
  visible: boolean;
  citations: CitationItem[];
}

export function CitationPanel({ visible, citations }: CitationPanelProps) {
  if (!visible || citations.length === 0) {
    return null;
  }

  return (
    <CitationsPanel
      citations={citations.map((citation) => ({
        paper_id: citation.paper_id,
        title: citation.title,
        authors: citation.authors || [],
        year: citation.year || 0,
        page: citation.page_num || citation.page || 1,
        snippet: citation.text_preview || citation.snippet || '',
        score: citation.score || 0,
        content_type: citation.content_type || 'text',
        chunk_id: citation.source_id || citation.chunk_id,
      }))}
    />
  );
}
