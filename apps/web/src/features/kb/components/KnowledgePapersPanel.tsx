import { useNavigate } from 'react-router';
import { PaperListItem } from '@/app/components/PaperListItem';
import { UnifiedEmptyState, UnifiedLoadingState } from '@/app/components/UnifiedFeedbackState';
import type { KBPaperListItem } from '@/services/kbApi';

interface KnowledgePapersPanelProps {
  papers: KBPaperListItem[];
  loading: boolean;
  onImport: () => void;
}

export function KnowledgePapersPanel({ papers, loading, onImport }: KnowledgePapersPanelProps) {
  const navigate = useNavigate();

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
        <PaperListItem
          key={paper.id}
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
      ))}
    </div>
  );
}
