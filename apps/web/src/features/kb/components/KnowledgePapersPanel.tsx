import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router';
import { PaperListItem } from '@/app/components/PaperListItem';
import { UnifiedEmptyState, UnifiedLoadingState } from '@/app/components/UnifiedFeedbackState';
import type { KBPaperListItem } from '@/services/kbApi';

interface KnowledgePapersPanelProps {
  highlightedPaperId?: string | null;
  papers: KBPaperListItem[];
  loading: boolean;
  onImport: () => void;
}

export function KnowledgePapersPanel({ highlightedPaperId, papers, loading, onImport }: KnowledgePapersPanelProps) {
  const navigate = useNavigate();
  const highlightedPaperRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!highlightedPaperId || !highlightedPaperRef.current) {
      return;
    }

    highlightedPaperRef.current.scrollIntoView({ block: 'center', behavior: 'smooth' });
  }, [highlightedPaperId, papers]);

  if (loading) {
    return <UnifiedLoadingState label="正在加载论文列表..." />;
  }

  if (papers.length === 0) {
    return (
      <UnifiedEmptyState
        title="当前知识库还没有论文"
        description="导入第一篇论文后即可开始检索、问答和笔记。"
        actionLabel="导入第一篇论文"
        onAction={onImport}
      />
    );
  }

  return (
    <div className="space-y-4">
      {papers.map((paper) => (
        <div
          key={paper.id}
          ref={paper.id === highlightedPaperId ? highlightedPaperRef : null}
          className={paper.id === highlightedPaperId ? 'rounded-2xl ring-2 ring-primary/40 ring-offset-2 ring-offset-background' : undefined}
        >
          <PaperListItem
            id={paper.id}
            title={paper.title}
            authors={paper.authors?.join('、') || '未知作者'}
            year={paper.year ? String(paper.year) : '未知年份'}
            venue={paper.venue || '未标注来源'}
            chunkCount={paper.chunkCount || 0}
            parseStatus={
              ['pending', 'processing', 'completed', 'failed'].includes(paper.status)
                ? (paper.status as 'pending' | 'processing' | 'completed' | 'failed')
                : 'pending'
            }
            entityCount={paper.entityCount || 0}
            onRead={() => navigate(`/read/${paper.id}`)}
            onNotes={() => navigate(`/notes?paperId=${paper.id}`)}
            onQuery={(paperId) => navigate(`/chat?paperId=${paperId}`)}
          />
        </div>
      ))}
    </div>
  );
}
