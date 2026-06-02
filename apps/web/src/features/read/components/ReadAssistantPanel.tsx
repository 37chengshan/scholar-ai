import { useMemo, useState } from 'react';

import type { Annotation } from '@/services/annotationsApi';
import * as annotationsApi from '@/services/annotationsApi';
import type { EvidenceBlockDto } from '@scholar-ai/types';
import type { ReadingCardDoc } from '@/features/read/readingCard';

import { AISummaryPanel } from '@/app/components/AISummaryPanel';
import { measureEvidenceBlock } from '@/lib/text-layout/evidence';
import { NotesEditor } from '@/app/components/NotesEditor';
import { Button } from '@/app/components/ui/button';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/app/components/ui/tabs';
import { EvidenceSideNote } from '@/features/read/components/EvidenceSideNote';
import { SourceChunkHighlight } from '@/features/read/components/SourceChunkHighlight';
import { navigateToSafeTarget } from '@/lib/navigation';
import { clsx } from 'clsx';
import { FileText, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

type ReadRightTab = 'notes' | 'annotations' | 'summary';

interface ReadAssistantPanelProps {
  id: string;
  isZh: boolean;
  rightTab: ReadRightTab;
  currentPage: number;
  linkedNoteId: string | null;
  linkedNoteContent: any;
  linkedNoteTitle: string;
  noteSaveStatus: 'idle' | 'pending' | 'saving' | 'saved' | 'error';
  noteLastSaved: Date | null;
  annotations: Annotation[];
  selectedText: string;
  selectionPosition: {
    x: number;
    y: number;
    width: number;
    height: number;
  } | null;
  source: string;
  sourceId: string;
  sourcePage: number;
  activeEvidence: EvidenceBlockDto | null;
  activeEvidencePreview: string;
  highlightedSourceChunkId: string;
  hasHighlight: boolean;
  readingSummary: string | null | undefined;
  readingCardDoc: ReadingCardDoc | null | undefined;
  onSetRightTab: (tab: ReadRightTab) => void;
  onSetLinkedNoteContent: (value: any) => void;
  onAnnotationCreated: () => Promise<void>;
  onNavigate: (path: string) => void;
  onSaveEvidence: (claim: string, block: EvidenceBlockDto) => Promise<void>;
  onOpenCitation: (url: string) => void;
  onInsertCurrentPageReference: () => void;
  onJumpAnnotationPage: (page: number) => void;
}

export function ReadAssistantPanel({
  id,
  isZh,
  rightTab,
  currentPage,
  linkedNoteId,
  linkedNoteContent,
  linkedNoteTitle,
  noteSaveStatus,
  noteLastSaved,
  annotations,
  selectedText,
  selectionPosition,
  source,
  sourceId,
  sourcePage,
  activeEvidence,
  activeEvidencePreview,
  highlightedSourceChunkId,
  hasHighlight,
  readingSummary,
  readingCardDoc,
  onSetRightTab,
  onSetLinkedNoteContent,
  onAnnotationCreated,
  onNavigate,
  onSaveEvidence,
  onOpenCitation,
  onInsertCurrentPageReference,
  onJumpAnnotationPage,
}: ReadAssistantPanelProps) {
  const [colorFilter, setColorFilter] = useState<string | null>(null);

  // Pre-calculate evidence block height to prevent layout shift
  const evidenceMinHeight = useMemo(() => {
    if (!activeEvidence?.text) return undefined;
    const { height } = measureEvidenceBlock(activeEvidence, 280);
    return height;
  }, [activeEvidence]);

  const filteredAnnotations = colorFilter
    ? annotations.filter((a) => a.color === colorFilter)
    : annotations;

  const uniqueColors = Array.from(new Set(annotations.map((a) => a.color).filter(Boolean)));

  const handleDeleteAnnotation = async (annotationId: string) => {
    try {
      await annotationsApi.deleteAnnotation(annotationId);
      await onAnnotationCreated();
    } catch {
      toast.error(isZh ? '删除批注失败' : 'Failed to delete annotation');
    }
  };

  return (
    <Tabs
      value={rightTab}
      onValueChange={(value) => onSetRightTab(value as ReadRightTab)}
      className="flex h-full flex-col"
    >
      <div className="border-b border-border/50 bg-background/80 px-5 py-4 backdrop-blur-md">
        <div className="text-[10px] font-semibold text-muted-foreground">
          {isZh ? '阅读辅助' : 'Reading Assistant'}
        </div>
        <div className="mt-1 text-sm font-semibold text-foreground">
          {isZh ? '笔记 / 批注 / 摘要' : 'Notes / Annotations / Summary'}
        </div>
        {hasHighlight ? (
          <div
            className="mt-3 space-y-2"
            style={evidenceMinHeight ? { minHeight: evidenceMinHeight } : undefined}
          >
            <SourceChunkHighlight sourceChunkId={highlightedSourceChunkId} />
            <EvidenceSideNote
              source={source}
              sourceId={sourceId}
              page={sourcePage}
              paperId={id}
              targetNoteId={linkedNoteId}
              evidence={activeEvidence}
              previewText={activeEvidencePreview}
              onSaveEvidence={(claim, block) => void onSaveEvidence(claim, block)}
            />
          </div>
        ) : null}
      </div>

      <TabsList className="justify-start bg-transparent px-3 pt-3 shrink-0">
        <TabsTrigger value="notes" className="text-xs">
          {isZh ? '笔记' : 'Notes'}
        </TabsTrigger>
        <TabsTrigger value="annotations" className="text-xs">
          {isZh ? '批注' : 'Annotations'}
        </TabsTrigger>
        <TabsTrigger value="summary" className="text-xs">
          {isZh ? 'AI总结' : 'AI Summary'}
        </TabsTrigger>
      </TabsList>

      <TabsContent value="annotations" className="mt-0 flex-1 overflow-hidden">
        <div className="flex h-full flex-col">
          {uniqueColors.length > 1 ? (
            <div className="flex items-center gap-1.5 border-b border-border/40 px-3 py-2">
              <span className="text-[10px] text-muted-foreground">
                {isZh ? '筛选:' : 'Filter:'}
              </span>
              <button
                onClick={() => setColorFilter(null)}
                className={clsx(
                  'rounded-sm px-1.5 py-0.5 text-[10px] transition-colors',
                  !colorFilter
                    ? 'bg-foreground/10 font-medium text-foreground'
                    : 'text-muted-foreground hover:text-foreground',
                )}
              >
                {isZh ? '全部' : 'All'}
              </button>
              {uniqueColors.map((c) => (
                <button
                  key={c}
                  onClick={() => setColorFilter(colorFilter === c ? null : c ?? null)}
                  className={clsx(
                    'h-4 w-4 rounded-sm border transition-all',
                    colorFilter === c
                      ? 'border-foreground/40 ring-1 ring-foreground/20 scale-110'
                      : 'border-border/40 hover:border-foreground/30',
                  )}
                  style={{ backgroundColor: c }}
                  title={c}
                />
              ))}
            </div>
          ) : null}
          <div className="flex-1 overflow-auto p-3">
            {filteredAnnotations.length === 0 ? (
              <p className="py-8 text-center text-xs text-muted-foreground">
                {isZh ? '暂无批注' : 'No annotations yet'}
              </p>
            ) : (
              <div className="space-y-2">
                {filteredAnnotations.map((annotation) => (
                  <div
                    key={annotation.id}
                    className="group relative cursor-pointer rounded-2xl border border-border/60 bg-background p-3 text-xs transition-colors hover:bg-amber-50/50"
                    onClick={() => {
                      onJumpAnnotationPage(annotation.pageNumber);
                      onSetRightTab('annotations');
                    }}
                    style={{
                      borderLeftColor: annotation.color,
                      borderLeftWidth: 3,
                    }}
                  >
                    <p className="text-muted-foreground">
                      {isZh ? '第' : 'Page'} {annotation.pageNumber}
                    </p>
                    {annotation.content ? <p className="mt-1 text-foreground">{annotation.content}</p> : null}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        void handleDeleteAnnotation(annotation.id);
                      }}
                      className="absolute right-2 top-2 rounded p-1 text-muted-foreground/50 opacity-0 transition-all hover:bg-destructive/10 hover:text-destructive group-hover:opacity-100"
                      aria-label={isZh ? '删除批注' : 'Delete annotation'}
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </TabsContent>

      <TabsContent value="summary" className="mt-0 flex-1 overflow-hidden">
        <AISummaryPanel
          paperId={id}
          summary={readingSummary}
          readingCardDoc={readingCardDoc}
          onJumpCitation={(block) => {
            onOpenCitation(block.citation_jump_url);
          }}
          onSaveEvidence={(claim, block) => {
            void onSaveEvidence(claim, block);
          }}
        />
      </TabsContent>

      <TabsContent value="notes" className="mt-0 flex-1 overflow-hidden">
        <div className="flex h-full flex-col">
          <div className="flex items-center justify-between border-b border-border/60 px-3 py-3">
            <span className="text-xs font-medium text-muted-foreground">
              {isZh ? '阅读笔记' : 'Reading Notes'}
            </span>
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-muted-foreground">
                {noteSaveStatus === 'saving' && (isZh ? '保存中' : 'Saving...')}
                {noteSaveStatus === 'pending' && (isZh ? '有未保存修改' : 'Unsaved changes')}
                {noteSaveStatus === 'saved' && noteLastSaved && `${isZh ? '已保存' : 'Saved'} ${noteLastSaved.toLocaleTimeString(isZh ? 'zh-CN' : 'en-US', { hour: '2-digit', minute: '2-digit' })}`}
                {noteSaveStatus === 'error' && (isZh ? '保存失败，稍后重试' : 'Save failed, retry later')}
              </span>
              <Button
                variant="outline"
                size="sm"
                className="h-8 rounded-full border-border/70 bg-background px-3 text-[10px]"
                onClick={() => onNavigate(`/notes?paperId=${id}${linkedNoteId ? `&noteId=${linkedNoteId}` : ''}`)}
              >
                <FileText className="mr-1 h-3 w-3" />
                {isZh ? '在笔记页编辑' : 'Open full notes'}
              </Button>
            </div>
          </div>
          <div className="border-b border-border/50 bg-background/80 px-3 py-2">
            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-[10px]"
              onClick={() => {
                onInsertCurrentPageReference();
                toast.success(isZh ? '已插入当前页引用' : 'Inserted current page reference');
              }}
            >
              {isZh ? '插入当前页引用' : 'Insert current page reference'}
            </Button>
          </div>
          <div className="flex-1 overflow-hidden">
            <NotesEditor
              content={linkedNoteContent}
              onChange={onSetLinkedNoteContent}
              placeholder={
                isZh
                  ? '添加阅读笔记... 使用 [[pdf:paperId:page:5]] 引用论文'
                  : 'Add reading notes... Use [[pdf:paperId:page:5]] to reference'
              }
            />
          </div>
        </div>
      </TabsContent>
    </Tabs>
  );
}
