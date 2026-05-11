import { FileText } from 'lucide-react';

import type { EvidenceBlockDto } from '@scholar-ai/types';

import { Button } from '@/app/components/ui/button';
import { navigateToSafeTarget } from '@/lib/navigation';
import { ReadAssistantPanel } from '@/features/read/components/ReadAssistantPanel';
import { ReadTopToolbar } from '@/features/read/components/ReadTopToolbar';
import { ReadWorkspace } from '@/features/read/components/ReadWorkspace';
import { createEmptyEditorDocument } from '@/features/notes/ownership';
import { useReadWorkspaceScreen } from '@/features/read/hooks/useReadWorkspaceScreen';

export function ReadWorkspaceScreen() {
  const workspace = useReadWorkspaceScreen();
  const {
    id,
    navigate,
    isZh,
    sourceNav,
    chunkHighlight,
    saveEvidence,
    paper,
    loading,
    error,
    currentPage,
    totalPages,
    scale,
    annotations,
    selectedText,
    selectionPosition,
    activeAnnotationId,
    activeEvidence,
    activeEvidencePreview,
    linkedNoteId,
    linkedNoteTitle,
    linkedNoteContent,
    noteSaveStatus,
    noteLastSaved,
    pageInputValue,
    isDesktopViewport,
    rightTab,
    isPanelOpen,
    isFullscreen,
    clampPage,
    setScale,
    setSelectedText,
    setSelectionPosition,
    setLinkedNoteContent,
    setPageInputValue,
    setRightTab,
    setIsPanelOpen,
    goToPage,
    handleAnnotationCreated,
    handleNumPagesChange,
    toggleFullscreen,
  } = workspace;

  if (!id) {
    return (
      <div className="flex h-full items-center justify-center bg-background">
        <div className="max-w-xl px-8 text-center">
          <div className="text-[10px] font-bold uppercase tracking-[0.28em] text-muted-foreground">
            {isZh ? '阅读工作台' : 'Reading Workspace'}
          </div>
          <h1 className="mt-4 font-serif text-4xl font-semibold tracking-tight text-foreground">
            {isZh ? '选择一篇论文开始沉浸阅读' : 'Choose a paper to start focused reading'}
          </h1>
          <p className="mt-4 text-sm leading-7 text-muted-foreground">
            {isZh
              ? '左侧导航已经可以进入阅读页；接下来从知识库、检索结果或笔记引用里打开具体论文。'
              : 'The reading page is now directly reachable. Open a paper from knowledge bases, search results, or linked notes to continue.'}
          </p>
          <div className="mt-8 flex items-center justify-center gap-3">
            <Button onClick={() => navigate('/knowledge-bases')} className="rounded-full px-5">
              {isZh ? '前往知识库' : 'Open Knowledge Bases'}
            </Button>
            <Button variant="outline" onClick={() => navigate('/search')} className="rounded-full px-5">
              {isZh ? '前往检索' : 'Go to Search'}
            </Button>
          </div>
        </div>
      </div>
    );
  }

  if (loading || !paper) {
    return (
      <div className="flex h-full items-center justify-center">
        {error ? (
          <div className="text-center">
            <p className="mb-4 text-destructive">{error}</p>
            <Button onClick={() => navigate('/knowledge-bases')}>
              {isZh ? '返回知识库' : 'Back to Knowledge Bases'}
            </Button>
          </div>
        ) : isZh ? (
          '加载中...'
        ) : (
          'Loading...'
        )}
      </div>
    );
  }

  const assistantPanelContent = (
    <ReadAssistantPanel
      id={id}
      isZh={isZh}
      rightTab={rightTab}
      currentPage={currentPage}
      linkedNoteId={linkedNoteId}
      linkedNoteContent={linkedNoteContent}
      linkedNoteTitle={linkedNoteTitle}
      noteSaveStatus={noteSaveStatus}
      noteLastSaved={noteLastSaved}
      annotations={annotations}
      selectedText={selectedText}
      selectionPosition={selectionPosition}
      source={sourceNav.source}
      sourceId={sourceNav.sourceId}
      sourcePage={sourceNav.page}
      activeEvidence={activeEvidence}
      activeEvidencePreview={activeEvidencePreview}
      highlightedSourceChunkId={chunkHighlight.highlightedSourceChunkId}
      hasHighlight={chunkHighlight.hasHighlight}
      readingSummary={paper.readingNotes}
      readingCardDoc={paper.readingCardDoc}
      onSetRightTab={setRightTab}
      onSetLinkedNoteContent={setLinkedNoteContent}
      onAnnotationCreated={handleAnnotationCreated}
      onNavigate={navigate}
      onSaveEvidence={(claim, block: EvidenceBlockDto) => saveEvidence(claim, block, {
        surface: 'read',
        targetNoteId: linkedNoteId || undefined,
      })}
      onOpenCitation={(url) => navigateToSafeTarget(url, navigate)}
      onInsertCurrentPageReference={() => {
        const refText = `[[pdf:${id}:page:${currentPage}]]`;
        const current = linkedNoteContent || createEmptyEditorDocument();
        setLinkedNoteContent({
          ...current,
          content: [
            ...((current.content as any[]) || []),
            { type: 'paragraph', content: [{ type: 'text', text: refText }] },
          ],
        });
      }}
      onJumpAnnotationPage={(page) => {
        void goToPage(clampPage(page), 'annotation');
      }}
    />
  );

  return (
    <div className="editorial-app-shell flex h-full min-h-0 flex-col bg-background">
      <ReadTopToolbar
        id={id}
        isZh={isZh}
        title={paper.title}
        currentPage={currentPage}
        totalPages={totalPages}
        pageInputValue={pageInputValue}
        scale={scale}
        isFullscreen={isFullscreen}
        isPanelOpen={isPanelOpen}
        linkedNoteId={linkedNoteId}
        sourceId={sourceNav.sourceId}
        navigate={navigate}
        onPageInputChange={(value) => setPageInputValue(value.replace(/[^0-9]/g, ''))}
        onPageInputSubmit={() => {
          const next = Number(pageInputValue || '1');
          if (Number.isNaN(next)) {
            setPageInputValue(String(currentPage));
            return;
          }
          void goToPage(next, 'toolbar');
        }}
        onGoPrevPage={() => {
          void goToPage(Math.max(1, currentPage - 1), 'toolbar');
        }}
        onGoNextPage={() => {
          void goToPage(clampPage(currentPage + 1), 'toolbar');
        }}
        onZoomOut={() => setScale((value) => Math.max(0.5, value - 0.1))}
        onZoomIn={() => setScale((value) => Math.min(2, value + 0.1))}
        onToggleFullscreen={toggleFullscreen}
        onTogglePanel={() => setIsPanelOpen(!isPanelOpen)}
      />

      <ReadWorkspace
        id={id}
        isZh={isZh}
        currentPage={currentPage}
        scale={scale}
        isPanelOpen={isPanelOpen}
        isDesktopViewport={isDesktopViewport}
        paperImradJson={paper.imradJson}
        annotations={annotations}
        activeEvidence={activeEvidence}
        activeAnnotationId={activeAnnotationId}
        assistantPanelContent={assistantPanelContent}
        onPageSelect={(page, reason) => {
          void goToPage(clampPage(page), reason);
        }}
        onNumPagesChange={handleNumPagesChange}
        onTextSelection={(selection) => {
          setSelectedText(selection?.text || '');
          setSelectionPosition(selection?.position || null);
        }}
        onPanelOpenChange={setIsPanelOpen}
        onSetRightTab={setRightTab}
      />
    </div>
  );
}
