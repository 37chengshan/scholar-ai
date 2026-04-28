import type { EvidenceBlock } from '@/features/chat/components/workspaceTypes';
import { SourceChunkLink } from './SourceChunkLink';

interface EvidenceBlockCardProps {
  block: EvidenceBlock;
  onOpenSource: (sourceChunkId: string, paperId?: string, pageNum?: number | null) => void;
  onSave: (block: EvidenceBlock) => void;
}

export function EvidenceBlockCard({ block, onOpenSource, onSave }: EvidenceBlockCardProps) {
  return (
    <article className="rounded-lg border border-border/60 bg-background/70 p-2.5">
      <div className="mb-1 flex items-center justify-between gap-2 text-[11px] text-muted-foreground">
        <span>{block.paper_id} · {block.section_path || 'unknown-section'}</span>
        <span>{block.content_type}</span>
      </div>
      <p className="line-clamp-4 text-xs leading-relaxed text-foreground/90">{block.text}</p>
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
          Save note
        </button>
      </div>
    </article>
  );
}
