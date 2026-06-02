import type { Annotation } from '@/services/annotationsApi';
import type { EvidenceBlockDto } from '@scholar-ai/types';

import { PDFViewer } from '@/app/components/PDFViewer';
import { SectionTree } from '@/app/components/SectionTree';
import { Sheet, SheetContent, SheetDescription, SheetTitle } from '@/app/components/ui/sheet';
import { ThumbnailStrip } from '@/app/components/ThumbnailStrip';
import { WorkspaceShell } from '@/app/components/layout/WorkspaceShell';

interface ReadWorkspaceProps {
  id: string;
  isZh: boolean;
  currentPage: number;
  scale: number;
  isPanelOpen: boolean;
  isDesktopViewport: boolean;
  paperImradJson: unknown;
  annotations: Annotation[];
  activeEvidence: EvidenceBlockDto | null;
  activeAnnotationId: string | null;
  assistantPanelContent: React.ReactNode;
  onPageSelect: (page: number, reason: 'toolbar' | 'thumbnail' | 'section' | 'citation' | 'annotation' | 'url') => void;
  onNumPagesChange: (numPages: number) => void;
  onTextSelection: (selection: { text: string; position: { x: number; y: number; width: number; height: number }; rect?: DOMRect } | null) => void;
  onPanelOpenChange: (value: boolean) => void;
  onSetRightTab: (tab: 'notes' | 'annotations' | 'summary') => void;
}

export function ReadWorkspace({
  id,
  isZh,
  currentPage,
  scale,
  isPanelOpen,
  isDesktopViewport,
  paperImradJson,
  annotations,
  activeEvidence,
  activeAnnotationId,
  assistantPanelContent,
  onPageSelect,
  onNumPagesChange,
  onTextSelection,
  onPanelOpenChange,
  onSetRightTab,
}: ReadWorkspaceProps) {
  return (
    <>
      <div className="flex min-h-0 flex-1 bg-background">
        <WorkspaceShell
          layoutId="read"
          sidebar={(
            <div className="flex h-full w-full flex-col pt-2">
              <div className="shrink-0 border-b border-border/50 px-5 py-3">
                <h2 className="font-serif text-[10px] font-bold uppercase tracking-[0.2em] tracking-tight text-muted-foreground">
                  {isZh ? '论文章节' : 'Sections'}
                </h2>
              </div>
              <div className="relative flex-1 overflow-auto">
                <SectionTree
                  imrad={paperImradJson}
                  onPageSelect={(page) => onPageSelect(page, 'section')}
                  currentPage={currentPage}
                  isZh={isZh}
                />
              </div>
            </div>
          )}
          main={(
            <div className="flex h-full w-full min-w-0 flex-col">
              <div className="flex flex-1 flex-col overflow-hidden">
                <PDFViewer
                  paperId={id}
                  currentPage={currentPage}
                  scale={scale}
                  showControls={false}
                  onNumPagesChange={onNumPagesChange}
                  annotations={annotations}
                  activeAnnotationId={activeAnnotationId}
                  highlightSnippet={activeEvidence?.text || ''}
                  onPageChange={(page) => onPageSelect(page, 'toolbar')}
                  onTextSelection={(selection) => {
                    onTextSelection(selection);
                    if (typeof window !== 'undefined' && window.innerWidth >= 1024) {
                      onPanelOpenChange(Boolean(selection));
                    }
                    if (selection) {
                      onSetRightTab('annotations');
                    }
                  }}
                />
              </div>

              <div className="h-28 shrink-0 border-t bg-muted/10">
                <ThumbnailStrip
                  paperId={id}
                  currentPage={currentPage}
                  onPageClick={(page) => onPageSelect(page, 'thumbnail')}
                  thumbnailWidth={60}
                />
              </div>
            </div>
          )}
          inspector={
            isPanelOpen && isDesktopViewport ? (
              <div className="h-full w-full border-l border-border/50 bg-stone-50/20">
                {assistantPanelContent}
              </div>
            ) : undefined
          }
        />
      </div>

      {!isDesktopViewport ? (
        <Sheet open={isPanelOpen} onOpenChange={onPanelOpenChange}>
          <SheetContent side="right" className="w-[92vw] max-w-none border-l border-border/60 bg-background p-0 sm:max-w-md">
            <SheetTitle className="sr-only">{isZh ? '阅读辅助面板' : 'Reading assistant panel'}</SheetTitle>
            <SheetDescription className="sr-only">
              {isZh ? '查看阅读笔记、批注和 AI 总结。' : 'Review reading notes, annotations, and AI summary.'}
            </SheetDescription>
            <div className="h-full min-h-0 overflow-hidden">
              {assistantPanelContent}
            </div>
          </SheetContent>
        </Sheet>
      ) : null}
    </>
  );
}
