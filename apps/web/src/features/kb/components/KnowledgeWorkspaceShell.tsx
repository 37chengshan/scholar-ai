import { useMemo } from 'react';
import { useNavigate } from 'react-router';
import { ArrowLeft, Database, Library, Clock3, Search, MessageSquare, UploadCloud, Loader2 } from 'lucide-react';
import { Link } from 'react-router';
import { PaperTexture } from '@/app/components/PaperTexture';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/app/components/ui/tabs';
import { ImportDialog } from '@/app/components/ImportDialog';
import { UnifiedErrorState, UnifiedLoadingState } from '@/app/components/UnifiedFeedbackState';
import { toast } from 'sonner';
import { useKnowledgeBaseWorkspace } from '@/features/kb/hooks/useKnowledgeBaseWorkspace';
import { useImportWorkflow } from '@/features/kb/hooks/useImportWorkflow';
import { useImportJobsPolling } from '@/features/kb/hooks/useImportJobsPolling';
import { KnowledgePapersPanel } from '@/features/kb/components/KnowledgePapersPanel';
import { KnowledgeImportPanel } from '@/features/kb/components/KnowledgeImportPanel';
import { KnowledgeEvidencePanel } from '@/features/kb/components/KnowledgeEvidencePanel';
import { KnowledgeRunHistoryPanel } from '@/features/kb/components/KnowledgeRunHistoryPanel';
import { KnowledgeQuickAskPanel } from '@/features/kb/components/KnowledgeQuickAskPanel';
import { KnowledgeReviewPanel } from '@/features/kb/components/KnowledgeReviewPanel';
import { useKnowledgeRuns } from '@/features/kb/hooks/useKnowledgeRuns';
import { useKnowledgeWorkflowRefresh } from '@/features/kb/hooks/useKnowledgeWorkflowRefresh';
import { UploadWorkspace } from '@/features/uploads/components/UploadWorkspace';
import { buildKnowledgeBaseReadinessItems } from '@/features/workflow/commandCenter';

export function KnowledgeWorkspaceShell() {
  const navigate = useNavigate();
  const {
    activeTab,
    isImportDialogOpen,
    importedPaperId,
    queries,
    search,
    setImportDialogOpen,
    refreshAll,
    syncTab,
  } = useKnowledgeBaseWorkspace();
  const { kbId, kb, papers, importJobs, loadingKB, papersLoading, loadImportJobs, loadPapers, loadKnowledgeBase } = queries;
  const { runs, loadingRuns, reloadRuns } = useKnowledgeRuns(kbId);

  const hasRunningJobs = importJobs.some(
    (job) => job.status === 'created' || job.status === 'running' || job.status === 'awaiting_user_action'
  );

  useImportJobsPolling({
    enabled: hasRunningJobs,
    intervalMs: 5000,
    onTick: async () => {
      await loadImportJobs({ silent: true });
    },
  });

  const { handleImportCompleted } = useImportWorkflow({
    onImportComplete: async () => {
      await refreshImportStatus({ refreshDerivedOnCompleted: true });
    },
  });

  const { refreshImportStatus } = useKnowledgeWorkflowRefresh({
    importJobs,
    loadImportJobs,
    loadPapers,
    loadKnowledgeBase,
    reloadRuns,
  });
  const readinessItems = useMemo(() => {
    if (!kb) {
      return [];
    }
    return buildKnowledgeBaseReadinessItems({ kb, importJobs, runs });
  }, [importJobs, kb, runs]);

  if (loadingKB) {
    return (
      <div className="relative min-h-screen bg-background">
        <PaperTexture />
        <UnifiedLoadingState fullScreen={true} label="正在加载知识库..." />
      </div>
    );
  }

  if (!kb || !kbId) {
    return (
      <div className="relative min-h-screen bg-background">
        <PaperTexture />
        <div className="min-h-[60vh] flex items-center justify-center">
          <UnifiedErrorState
            title="知识库不存在或已删除"
            description="该资源可能已被移除，或当前账号无访问权限。"
            retryLabel="返回列表"
            onRetry={() => navigate('/knowledge-bases')}
            className="max-w-md"
          />
        </div>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen bg-background">
      <PaperTexture />
      <div className="space-y-6 pb-20 px-6 max-w-7xl mx-auto relative z-10">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-5 pb-5 magazine-hairline">
          <div className="space-y-3">
            <Link
              to="/knowledge-bases"
              className="mb-1 inline-flex items-center gap-2 text-xs font-bold uppercase tracking-[0.16em] text-muted-foreground transition-colors hover:text-primary"
              onClick={(event) => {
                event.preventDefault();
                navigate('/knowledge-bases');
              }}
            >
              <ArrowLeft className="w-4 h-4" />
              返回知识库列表
            </Link>
            <div className="flex items-center gap-4">
              <h1 className="text-3xl md:text-4xl font-black font-serif uppercase tracking-tight text-foreground leading-none">
                {kb.name}
              </h1>
              <span className="border border-border/70 bg-paper-1 px-2.5 py-1 font-mono text-xs text-muted-foreground">
                {kbId}
              </span>
            </div>
            <div className="flex flex-wrap gap-4 pt-1 text-xs font-bold uppercase tracking-[0.14em] text-muted-foreground">
              <span className="flex items-center gap-2">
                <Database className="w-4 h-4" /> {kb.embeddingModel} Model
              </span>
              <span className="flex items-center gap-2 text-primary">★ {kb.parseEngine} Engine</span>
              <span>{kb.paperCount} Papers</span>
              <span>{kb.chunkCount} Chunks</span>
            </div>
          </div>

          <div className="flex items-center gap-4 shrink-0">
            <button
              onClick={() => syncTab('uploads')}
              className="flex items-center gap-2 border border-border/80 bg-paper-1 text-foreground px-4 py-2.5 font-bold uppercase tracking-[0.14em] text-xs transition-colors hover:border-primary hover:text-primary"
            >
              <UploadCloud className="w-4 h-4" />
              上传工作台
            </button>
            <button
              onClick={() => setImportDialogOpen(true)}
              className="flex items-center gap-2 border border-border/80 bg-paper-1 text-foreground px-4 py-2.5 font-bold uppercase tracking-[0.14em] text-xs transition-colors hover:border-primary hover:text-primary"
            >
              <UploadCloud className="w-4 h-4" />
              导入来源
            </button>
            <button
              onClick={() => navigate(`/chat?kbId=${kb.id}`)}
              className="flex items-center gap-2 bg-primary hover:bg-primary/90 text-white px-4 py-2.5 font-bold uppercase tracking-[0.14em] text-xs transition-colors"
            >
              <MessageSquare className="w-4 h-4" />
              对整个知识库提问
            </button>
          </div>
        </div>

        <section className="rounded-2xl border border-border/80 bg-paper-1 p-4">
          <div className="mb-3 flex items-center justify-between gap-3">
            <div>
              <div className="text-[10px] font-bold uppercase tracking-[0.22em] text-muted-foreground">Readiness</div>
              <h2 className="mt-1 font-serif text-xl font-semibold text-foreground">Import to evidence to action</h2>
            </div>
            <button
              type="button"
              onClick={() => void refreshAll({ silent: true })}
              className="rounded-full border border-border/70 bg-background px-3 py-1.5 text-[10px] font-bold uppercase tracking-[0.12em] text-foreground/75 transition-colors hover:border-primary/40 hover:text-primary"
            >
              Refresh
            </button>
          </div>
          <div className="grid gap-3 lg:grid-cols-5">
            {readinessItems.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => navigate(item.targetHref)}
                className="rounded-xl border border-border/70 bg-background/80 p-3 text-left transition-colors hover:border-primary/40 hover:bg-primary/[0.03]"
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="text-[10px] font-bold uppercase tracking-[0.16em] text-muted-foreground">
                    {item.title}
                  </div>
                  <span
                    className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                      item.priority === 'blocked'
                        ? 'bg-rose-500/10 text-rose-700'
                        : item.priority === 'active'
                          ? 'bg-blue-500/10 text-blue-700'
                          : 'bg-emerald-500/10 text-emerald-700'
                    }`}
                  >
                    {item.statusLabel}
                  </span>
                </div>
                <div className="mt-2 text-xs leading-relaxed text-muted-foreground">{item.reason}</div>
                <div className="mt-3 text-[11px] font-medium text-foreground/80">Open target</div>
              </button>
            ))}
          </div>
        </section>

        <Tabs value={activeTab} onValueChange={syncTab} className="w-full">
          <TabsList className="flex h-auto w-full flex-wrap justify-start gap-0 border-b border-border/80 bg-transparent p-0">
            <TabsTrigger value="papers" className={`flex-1 sm:flex-none px-8 py-4 font-bold uppercase tracking-widest text-sm transition-all outline-none border-b-4 rounded-none bg-transparent ${
              activeTab === 'papers'
                ? 'border-primary text-foreground bg-transparent'
                : 'border-transparent text-muted-foreground hover:text-foreground hover:bg-primary/[0.04]'
            }`}>
              <span className="flex items-center justify-center gap-2"><Library className="w-4 h-4" /> 论文列表</span>
            </TabsTrigger>
            <TabsTrigger value="import-status" className={`flex-1 sm:flex-none px-8 py-4 font-bold uppercase tracking-widest text-sm transition-all outline-none border-b-4 rounded-none bg-transparent ${
              activeTab === 'import-status'
                ? 'border-primary text-foreground bg-transparent'
                : 'border-transparent text-muted-foreground hover:text-foreground hover:bg-primary/[0.04]'
            }`}>
              <span className="flex items-center justify-center gap-2"><Clock3 className="w-4 h-4" /> 导入状态</span>
            </TabsTrigger>
            <TabsTrigger value="uploads" className={`flex-1 sm:flex-none px-8 py-4 font-bold uppercase tracking-widest text-sm transition-all outline-none border-b-4 rounded-none bg-transparent ${
              activeTab === 'uploads'
                ? 'border-primary text-foreground bg-transparent'
                : 'border-transparent text-muted-foreground hover:text-foreground hover:bg-primary/[0.04]'
            }`}>
              <span className="flex items-center justify-center gap-2"><UploadCloud className="w-4 h-4" /> 上传工作台</span>
            </TabsTrigger>
            <TabsTrigger value="search" className={`flex-1 sm:flex-none px-8 py-4 font-bold uppercase tracking-widest text-sm transition-all outline-none border-b-4 rounded-none bg-transparent ${
              activeTab === 'search'
                ? 'border-primary text-foreground bg-transparent'
                : 'border-transparent text-muted-foreground hover:text-foreground hover:bg-primary/[0.04]'
            }`}>
              <span className="flex items-center justify-center gap-2"><Search className="w-4 h-4" /> 知识库检索</span>
            </TabsTrigger>
            <TabsTrigger value="runs" className={`flex-1 sm:flex-none px-8 py-4 font-bold uppercase tracking-widest text-sm transition-all outline-none border-b-4 rounded-none bg-transparent ${
              activeTab === 'runs'
                ? 'border-primary text-foreground bg-transparent'
                : 'border-transparent text-muted-foreground hover:text-foreground hover:bg-primary/[0.04]'
            }`}>
              <span className="flex items-center justify-center gap-2"><MessageSquare className="w-4 h-4" /> Run 历史</span>
            </TabsTrigger>
            <TabsTrigger value="review" className={`flex-1 sm:flex-none px-8 py-4 font-bold uppercase tracking-widest text-sm transition-all outline-none border-b-4 rounded-none bg-transparent ${
              activeTab === 'review'
                ? 'border-primary text-foreground bg-transparent'
                : 'border-transparent text-muted-foreground hover:text-foreground hover:bg-primary/[0.04]'
            }`}>
              <span className="flex items-center justify-center gap-2"><MessageSquare className="w-4 h-4" /> Review Draft</span>
            </TabsTrigger>
            <TabsTrigger value="chat" className={`flex-1 sm:flex-none px-8 py-4 font-bold uppercase tracking-widest text-sm transition-all outline-none border-b-4 rounded-none bg-transparent ${
              activeTab === 'chat'
                ? 'border-primary text-foreground bg-transparent'
                : 'border-transparent text-muted-foreground hover:text-foreground hover:bg-primary/[0.04]'
            }`}>
              <span className="flex items-center justify-center gap-2"><MessageSquare className="w-4 h-4" /> 问答</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="papers" className="mt-8 space-y-6 outline-none animate-in fade-in slide-in-from-bottom-4 duration-500">
            <KnowledgePapersPanel
              papers={papers}
              loading={papersLoading}
              highlightedPaperId={importedPaperId}
              onImport={() => setImportDialogOpen(true)}
            />
          </TabsContent>

          <TabsContent value="import-status" className="mt-8 outline-none animate-in fade-in slide-in-from-bottom-4 duration-500">
            <KnowledgeImportPanel
              importJobs={importJobs}
              onJobComplete={() => {
                void refreshImportStatus({ refreshDerivedOnCompleted: true });
              }}
            />
          </TabsContent>

          <TabsContent value="uploads" className="mt-8 outline-none animate-in fade-in slide-in-from-bottom-4 duration-500">
            <UploadWorkspace
              knowledgeBaseId={kb.id}
              onQueueComplete={() => {
                void refreshImportStatus({ refreshDerivedOnCompleted: true });
              }}
            />
          </TabsContent>

          <TabsContent value="search" className="mt-8 outline-none animate-in fade-in slide-in-from-bottom-4 duration-500">
            <KnowledgeEvidencePanel
              searchQuery={search.searchDraft}
              isSearching={search.isSearching}
              results={search.results}
              papersEmpty={!papersLoading && papers.length === 0}
              onSearchQueryChange={search.setSearchDraft}
              onSearchSubmit={() => void search.search(search.searchDraft)}
              onOpenPaper={(paperId, page) => navigate(`/read/${paperId}?page=${page || 1}`)}
            />
          </TabsContent>

          <TabsContent value="runs" className="mt-8 outline-none animate-in fade-in slide-in-from-bottom-4 duration-500">
            <KnowledgeRunHistoryPanel
              runs={runs}
              loading={loadingRuns}
              onOpenRun={(runId) => navigate(`/knowledge-bases/${kb.id}?tab=review&runId=${runId}`)}
            />
          </TabsContent>

          <TabsContent value="review" className="mt-8 outline-none animate-in fade-in slide-in-from-bottom-4 duration-500">
            <KnowledgeReviewPanel kbId={kb.id} papers={papers} onRunChanged={() => void reloadRuns()} />
          </TabsContent>

          <TabsContent value="chat" className="mt-8 outline-none animate-in fade-in slide-in-from-bottom-4 duration-500">
            <KnowledgeQuickAskPanel kbId={kb.id} onEnterChat={() => navigate(`/chat?kbId=${kb.id}`)} />
          </TabsContent>
        </Tabs>
      </div>

      <ImportDialog
        open={isImportDialogOpen}
        onOpenChange={setImportDialogOpen}
        knowledgeBaseId={kb.id}
        knowledgeBaseName={kb.name}
        onImportComplete={() => {
          void handleImportCompleted();
          toast.success('导入任务已提交');
        }}
      />
    </div>
  );
}
