import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router';
import { FixedSizeList, type ListChildComponentProps } from 'react-window';
import { PaperListItem } from '@/app/components/PaperListItem';
import { UnifiedEmptyState, UnifiedLoadingState } from '@/app/components/UnifiedFeedbackState';
import type { KBPaperListItem } from '@/services/kbApi';

const VIRTUALIZATION_THRESHOLD = 40;
const PAPER_ROW_HEIGHT = 196;

interface PaperRowData {
  highlightedPaperId?: string | null;
  navigate: ReturnType<typeof useNavigate>;
  papers: KBPaperListItem[];
}

function PaperRow({ index, style, data }: ListChildComponentProps<PaperRowData>) {
  const paper = data.papers[index];
  const isHighlighted = paper.id === data.highlightedPaperId;

  return (
    <div style={style} className="box-border h-full px-1 py-2">
      <div
        className={isHighlighted ? 'rounded-2xl ring-2 ring-primary/40 ring-offset-2 ring-offset-background' : undefined}
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
          onRead={() => data.navigate(`/read/${paper.id}`)}
          onNotes={() => data.navigate(`/notes?paperId=${paper.id}`)}
          onQuery={(paperId) => data.navigate(`/chat?paperId=${paperId}`)}
        />
      </div>
    </div>
  );
}

interface KnowledgePapersPanelProps {
  highlightedPaperId?: string | null;
  papers: KBPaperListItem[];
  loading: boolean;
  onImport: () => void;
}

export function KnowledgePapersPanel({ highlightedPaperId, papers, loading, onImport }: KnowledgePapersPanelProps) {
  const navigate = useNavigate();
  const highlightedPaperRef = useRef<HTMLDivElement | null>(null);
  const listRef = useRef<FixedSizeList<PaperRowData> | null>(null);
  const isVirtualized = papers.length >= VIRTUALIZATION_THRESHOLD;

  useEffect(() => {
    if (!highlightedPaperId) {
      return;
    }

    if (isVirtualized) {
      const highlightedIndex = papers.findIndex((paper) => paper.id === highlightedPaperId);
      if (highlightedIndex >= 0) {
        listRef.current?.scrollToItem(highlightedIndex, 'center');
      }
      return;
    }

    if (!highlightedPaperRef.current) {
      return;
    }

    highlightedPaperRef.current.scrollIntoView({ block: 'center', behavior: 'smooth' });
  }, [highlightedPaperId, isVirtualized, papers]);

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

  if (isVirtualized) {
    const listHeight = Math.min(720, Math.max(360, papers.length * PAPER_ROW_HEIGHT));

    return (
      <FixedSizeList
        ref={listRef}
        height={listHeight}
        itemCount={papers.length}
        itemData={{ highlightedPaperId, navigate, papers }}
        itemKey={(index: number, data: PaperRowData) => data.papers[index].id}
        itemSize={PAPER_ROW_HEIGHT}
        width="100%"
      >
        {PaperRow}
      </FixedSizeList>
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
