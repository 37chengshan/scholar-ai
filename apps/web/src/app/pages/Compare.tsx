import { useLanguage } from '../contexts/LanguageContext';

import { CompareInspector } from '@/features/compare/components/CompareInspector';
import { CompareMainPanel } from '@/features/compare/components/CompareMainPanel';
import { CompareSidebar } from '@/features/compare/components/CompareSidebar';
import { useCompareWorkspace } from '@/features/compare/hooks/useCompareWorkspace';
import { WorkspaceShell } from '../components/layout/WorkspaceShell';

export function Compare() {
  const { language } = useLanguage();
  const isZh = language === 'zh';
  const {
    showInspector,
    selectedPapers,
    searchQuery,
    searchResults,
    searchLoading,
    enabledDims,
    question,
    compareResult,
    compareLoading,
    compareError,
    selectionNotice,
    insightCount,
    evidenceCount,
    setShowInspector,
    setSearchQuery,
    setQuestion,
    handleSearch,
    handleAddPaper,
    handleRemovePaper,
    handleToggleDim,
    handleCompare,
    handleJumpEvidence,
    handleSaveCellEvidence,
    handleSaveWholeCompare,
    handleContinueCellInChat,
    handleOpenChat,
  } = useCompareWorkspace(isZh);

  return (
    <div className="editorial-app-shell h-full min-h-0 bg-background">
      <WorkspaceShell
        layoutId="compare"
        sidebar={(
          <CompareSidebar
            isZh={isZh}
            selectedPapers={selectedPapers}
            selectionNotice={selectionNotice}
            searchQuery={searchQuery}
            searchLoading={searchLoading}
            searchResults={searchResults}
            enabledDims={enabledDims}
            question={question}
            compareLoading={compareLoading}
            onSearchQueryChange={setSearchQuery}
            onSearch={() => void handleSearch()}
            onAddPaper={handleAddPaper}
            onRemovePaper={handleRemovePaper}
            onToggleDim={handleToggleDim}
            onQuestionChange={setQuestion}
            onCompare={() => void handleCompare()}
          />
        )}
        main={(
          <CompareMainPanel
            isZh={isZh}
            showInspector={showInspector}
            selectedPaperCount={selectedPapers.length}
            compareResult={compareResult}
            compareLoading={compareLoading}
            compareError={compareError}
            onToggleInspector={() => setShowInspector((value) => !value)}
            onOpenChat={handleOpenChat}
            onSaveWholeCompare={() => void handleSaveWholeCompare()}
            onJumpEvidence={handleJumpEvidence}
            onSaveCellEvidence={handleSaveCellEvidence}
            onContinueCellInChat={handleContinueCellInChat}
          />
        )}
        inspector={showInspector ? (
          <CompareInspector
            isZh={isZh}
            selectedPapers={selectedPapers}
            question={question}
            insightCount={insightCount}
            evidenceCount={evidenceCount}
            compareResult={compareResult}
          />
        ) : undefined}
      />
    </div>
  );
}
