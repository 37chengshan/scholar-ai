import { Loader2 } from 'lucide-react';
import { useNavigate } from 'react-router';
import { Button } from '@/app/components/ui/button';
import { PaperListItem } from '@/app/components/PaperListItem';
import type { KBPaperListItem } from '@/services/kbApi';

interface KnowledgePapersPanelProps {
  papers: KBPaperListItem[];
  loading: boolean;
  onImport: () => void;
}

export function KnowledgePapersPanel({ papers, loading, onImport }: KnowledgePapersPanelProps) {
  const navigate = useNavigate();

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="w-6 h-6 animate-spin text-primary" />
      </div>
    );
  }

  if (papers.length === 0) {
    return (
      <div className="bg-white border-2 border-zinc-900 p-10 text-center space-y-4 shadow-[8px_8px_0px_0px_rgba(24,24,27,1)]">
        <div className="text-zinc-600 font-medium">当前知识库还没有论文</div>
        <Button onClick={onImport}>导入第一篇论文</Button>
      </div>
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
