import type { Annotation } from '@/services/annotationsApi';
import type { EvidenceBlockDto } from '@scholar-ai/types';
import type { ReadingCardDoc } from '@/features/read/readingCard';

import { AISummaryPanel } from '@/app/components/AISummaryPanel';
import { AnnotationToolbar } from '@/app/components/AnnotationToolbar';
import { NotesEditor } from '@/app/components/NotesEditor';
import { Button } from '@/app/components/ui/button';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/app/components/ui/tabs';
import { createEmptyEditorDocument } from '@/features/notes/ownership';
import { EvidenceSideNote } from '@/features/read/components/EvidenceSideNote';
import { SourceChunkHighlight } from '@/features/read/components/SourceChunkHighlight';
import { navigateToSafeTarget } from '@/lib/navigation';
import { FileText } from 'lucide-react';
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
          <div className="mt-3 space-y-2">
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
          <AnnotationToolbar
            paperId={id}
            pageNumber={currentPage}
            onAnnotationCreated={onAnnotationCreated}
            selectedText={selectedText}
            selectionPosition={selectionPosition}
          />
          <div className="flex-1 overflow-auto p-3">
            {annotations.length === 0 ? (
              <p className="py-8 text-center text-xs text-muted-foreground">
                {isZh ? '暂无批注' : 'No annotations yet'}
              </p>
            ) : (
              <div className="space-y-2">
                {annotations.map((annotation) => (
                  <div
                    key={annotation.id}
                    className="cursor-pointer rounded-2xl border border-border/60 bg-background p-3 text-xs transition-colors hover:bg-amber-50/50"
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
