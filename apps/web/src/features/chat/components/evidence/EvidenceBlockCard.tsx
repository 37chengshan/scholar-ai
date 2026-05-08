import type { EvidenceBlock } from '@/features/chat/components/workspaceTypes';
import { SourceChunkLink } from './SourceChunkLink';
import { useLanguage } from '@/app/contexts/LanguageContext';
import { normalizeEvidenceText } from '@/features/notes/content';

interface EvidenceBlockCardProps {
  block: EvidenceBlock;
  onOpenSource: (sourceChunkId: string, paperId?: string, pageNum?: number | null) => void;
  onSave: (block: EvidenceBlock) => void;
}

export function EvidenceBlockCard({ block, onOpenSource, onSave }: EvidenceBlockCardProps) {
  const { language } = useLanguage();
  const isZh = language === 'zh';
  const sectionLabel = block.section_path?.trim() || (isZh ? '正文片段' : 'Document excerpt');
  const pageLabel = block.page_num ? (isZh ? `第 ${block.page_num} 页` : `Page ${block.page_num}`) : null;
  const kindLabel = block.content_type === 'table'
    ? (isZh ? '表格' : 'Table')
    : block.content_type === 'figure'
      ? (isZh ? '图示' : 'Figure')
      : (isZh ? '正文' : 'Text');

  return (
    <article className="rounded-lg border border-border/60 bg-background/70 p-2.5">
      <div className="mb-1 flex items-center justify-between gap-2 text-[11px] text-muted-foreground">
        <span>{pageLabel ? `${pageLabel} · ${sectionLabel}` : sectionLabel}</span>
        <span>{kindLabel}</span>
      </div>
      <p className="line-clamp-4 text-xs leading-relaxed text-foreground/90">
        {normalizeEvidenceText(block.text)}
      </p>
      <div className="mt-2 flex items-center justify-between gap-2">
        <SourceChunkLink
          sourceChunkId={block.source_chunk_id}
          onOpen={(sourceChunkId) => onOpenSource(sourceChunkId, block.paper_id, block.page_num)}
        />
        <button
          type="button"
          className="rounded-md border border-border/70 px-2 py-1 text-[11px] hover:border-primary/40"
          onClick={() => onSave(block)}
        >
          {isZh ? '保存到笔记' : 'Save to notes'}
        </button>
      </div>
    </article>
  );
}
