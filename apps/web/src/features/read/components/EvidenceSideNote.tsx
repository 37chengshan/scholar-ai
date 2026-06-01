import type { EvidenceBlockDto } from '@scholar-ai/types';
import { useLanguage } from '@/app/contexts/LanguageContext';
import { normalizeEvidenceText } from '@/features/notes/content';
import { useTextMeasure, useElementWidth } from '@/lib/text-layout/react';
import { DEFAULT_TEXT_FONT } from '@/lib/text-layout/font';

interface EvidenceSideNoteProps {
  source: string;
  sourceId: string;
  page: number;
  paperId: string;
  targetNoteId: string | null;
  evidence: EvidenceBlockDto | null;
  previewText?: string;
  onSaveEvidence: (claim: string, block: EvidenceBlockDto) => void;
}

export function EvidenceSideNote({
  source,
  sourceId,
  page,
  paperId,
  targetNoteId,
  evidence,
  previewText = '',
  onSaveEvidence,
}: EvidenceSideNoteProps) {
  const { language } = useLanguage();
  const isZh = language === 'zh';
  const { width: containerWidth, setElement } = useElementWidth<HTMLDivElement>(280);

  // Measure 4 lines worth of height for accurate truncation
  const fourLineHeight = useTextMeasure(
    previewText || '',
    containerWidth,
    { ...DEFAULT_TEXT_FONT, size: 12, lineHeight: 18 },
  ).lineCount > 4
    ? 4 * 18
    : undefined;

  const evidenceSectionLabel = evidence?.section_path?.trim()
    ? evidence.section_path
    : (isZh ? '正文片段' : 'Document excerpt');

  if (!sourceId) {
    return null;
  }

  return (
    <div
      ref={setElement}
      className="rounded-md border border-border/70 bg-muted/20 px-3 py-2 text-xs"
    >
      <div className="font-semibold text-foreground/90">
        {isZh ? '证据侧注' : 'Evidence note'}
      </div>
      <div className="mt-1 text-muted-foreground">
        {isZh ? '来源：' : 'Source: '}
        {source === 'evidence'
          ? (isZh ? '问答证据' : 'Answer evidence')
          : source === 'chat'
            ? (isZh ? '对话引用' : 'Chat citation')
            : source}
      </div>
      <div className="text-muted-foreground">{isZh ? '位置：' : 'Section: '} {evidenceSectionLabel}</div>
      <div className="text-muted-foreground">
        {isZh ? '页码：' : 'Page: '}
        {page}
      </div>
      {previewText ? (
        <p
          className="mt-2 line-clamp-4 overflow-hidden text-foreground/90"
          style={fourLineHeight ? { maxHeight: fourLineHeight } : undefined}
        >
          {normalizeEvidenceText(previewText)}
        </p>
      ) : null}
      {evidence ? (
        <button
          type="button"
          className="mt-2 rounded-md border border-border/70 px-2 py-1 text-[11px] text-foreground hover:border-primary/50 hover:text-primary"
          onClick={() =>
            onSaveEvidence(
              isZh ? '当前阅读证据' : 'Current reading evidence',
              evidence,
            )
          }
        >
          {targetNoteId
            ? (isZh ? '加入当前笔记' : 'Add to current note')
            : (isZh ? '保存到笔记' : 'Save to notes')}
        </button>
      ) : null}
    </div>
  );
}
