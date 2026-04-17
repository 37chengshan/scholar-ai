import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router';
import { ArrowLeft, Database, Library, Clock3, Search, MessageSquare, UploadCloud, Loader2 } from 'lucide-react';
import { Link } from 'react-router';
import { PaperTexture } from '@/app/components/PaperTexture';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/app/components/ui/tabs';
import { ImportDialog } from '@/app/components/ImportDialog';
import { toast } from 'sonner';
import { useKnowledgeBaseWorkspace } from '@/features/kb/hooks/useKnowledgeBaseWorkspace';
import { useImportWorkflow } from '@/features/kb/hooks/useImportWorkflow';
import { useImportJobsPolling } from '@/features/kb/hooks/useImportJobsPolling';
import { KnowledgePapersPanel } from '@/features/kb/components/KnowledgePapersPanel';
import { KnowledgeImportPanel } from '@/features/kb/components/KnowledgeImportPanel';
import { KnowledgeEvidencePanel } from '@/features/kb/components/KnowledgeEvidencePanel';
import { KnowledgeRunHistoryPanel } from '@/features/kb/components/KnowledgeRunHistoryPanel';
import { KnowledgeQuickAskPanel } from '@/features/kb/components/KnowledgeQuickAskPanel';
import { useKnowledgeRuns } from '@/features/kb/hooks/useKnowledgeRuns';

export function KnowledgeWorkspaceShell() {
  const navigate = useNavigate();
  const {
    activeTab,
    isImportDialogOpen,
    queries,
    search,
    setImportDialogOpen,
    refreshAll,
    syncTab,
  } = useKnowledgeBaseWorkspace();
  const { runs, loadingRuns, reloadRuns } = useKnowledgeRuns();
  const previousImportJobStatus = useRef<Record<string, string>>({});

  const { kbId, kb, papers, importJobs, loadingKB, papersLoading, loadImportJobs, loadPapers, loadKnowledgeBase } = queries;

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
      await refreshAll({ silent: true });
    },
  });

  useEffect(() => {
    const hasNewlyCompletedJob = importJobs.some((job) => {
      const previousStatus = previousImportJobStatus.current[job.importJobId];
      return job.status === 'completed' && previousStatus !== 'completed';
    });

    previousImportJobStatus.current = importJobs.reduce<Record<string, string>>(
      (acc, job) => ({ ...acc, [job.importJobId]: job.status }),
      {}
    );

    if (hasNewlyCompletedJob) {
      void Promise.all([
        loadPapers({ silent: true }),
        loadKnowledgeBase({ silent: true }),
        reloadRuns(),
      ]);
    }
  }, [importJobs, loadKnowledgeBase, loadPapers, reloadRuns]);

  if (loadingKB) {
    return (
      <div className="relative min-h-screen bg-background">
        <PaperTexture />
        <div className="flex items-center justify-center min-h-[60vh]">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      </div>
    );
  }

  if (!kb || !kbId) {
    return (
      <div className="relative min-h-screen bg-background">
        <PaperTexture />
        <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
          <div className="text-zinc-500 font-medium">知识库不存在或已删除</div>
          <button
            onClick={() => navigate('/knowledge-bases')}
            className="bg-zinc-900 hover:bg-primary text-white px-6 py-3 font-bold uppercase tracking-wide"
          >
            返回列表
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen bg-background">
      <PaperTexture />
      <div className="space-y-8 pb-20 px-6 max-w-7xl mx-auto relative z-10">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 pb-6 border-b-4 border-zinc-900">
          <div className="space-y-4">
            <Link
              to="/knowledge-bases"
              className="inline-flex items-center gap-2 text-zinc-500 hover:text-primary transition-colors text-sm font-bold uppercase tracking-wider mb-2"
              onClick={(event) => {
                event.preventDefault();
                navigate('/knowledge-bases');
              }}
            >
              <ArrowLeft className="w-4 h-4" />
              返回知识库列表
            </Link>
            <div className="flex items-center gap-4">
              <h1 className="text-4xl md:text-5xl font-black font-serif uppercase tracking-tight text-zinc-900 leading-none">
                {kb.name}
              </h1>
              <span className="bg-zinc-100 border border-zinc-300 px-3 py-1 font-mono text-sm text-zinc-600 shadow-[2px_2px_0px_0px_rgba(24,24,27,0.2)]">
                {kbId}
              </span>
            </div>
            <div className="flex flex-wrap gap-4 text-sm font-bold uppercase tracking-wider text-zinc-500 pt-2">
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
              onClick={() => setImportDialogOpen(true)}
              className="flex items-center gap-2 bg-zinc-900 hover:bg-primary text-white px-6 py-4 font-bold uppercase tracking-wide transition-all shadow-[4px_4px_0px_0px_rgba(24,24,27,0.5)] hover:shadow-[4px_4px_0px_0px_rgba(211,84,0,0.8)] hover:-translate-y-1 hover:-translate-x-1"
            >
              <UploadCloud className="w-5 h-5" />
              导入来源
            </button>
            <button
              onClick={() => navigate(`/chat?kbId=${kb.id}`)}
              className="flex items-center gap-2 bg-primary hover:bg-zinc-900 text-white px-6 py-4 font-bold uppercase tracking-wide transition-all shadow-[4px_4px_0px_0px_rgba(24,24,27,0.5)] hover:shadow-[4px_4px_0px_0px_rgba(211,84,0,0.8)] hover:-translate-y-1 hover:-translate-x-1"
            >
              <MessageSquare className="w-5 h-5" />
              对整个知识库提问
            </button>
          </div>
        </div>

        <Tabs value={activeTab} onValueChange={syncTab} className="w-full">
          <TabsList className="flex flex-wrap border-b-2 border-zinc-200 bg-transparent h-auto p-0 gap-0 w-full justify-start">
            <TabsTrigger value="papers" className={`flex-1 sm:flex-none px-8 py-4 font-bold uppercase tracking-widest text-sm transition-all outline-none border-b-4 rounded-none bg-transparent ${
              activeTab === 'papers'
                ? 'border-primary text-primary bg-primary/5'
                : 'border-transparent text-zinc-500 hover:text-zinc-900 hover:bg-zinc-50'
            }`}>
              <span className="flex items-center justify-center gap-2"><Library className="w-4 h-4" /> 论文列表</span>
            </TabsTrigger>
            <TabsTrigger value="import-status" className={`flex-1 sm:flex-none px-8 py-4 font-bold uppercase tracking-widest text-sm transition-all outline-none border-b-4 rounded-none bg-transparent ${
              activeTab === 'import-status'
                ? 'border-primary text-primary bg-primary/5'
                : 'border-transparent text-zinc-500 hover:text-zinc-900 hover:bg-zinc-50'
            }`}>
              <span className="flex items-center justify-center gap-2"><Clock3 className="w-4 h-4" /> 导入状态</span>
            </TabsTrigger>
            <TabsTrigger value="search" className={`flex-1 sm:flex-none px-8 py-4 font-bold uppercase tracking-widest text-sm transition-all outline-none border-b-4 rounded-none bg-transparent ${
              activeTab === 'search'
                ? 'border-primary text-primary bg-primary/5'
                : 'border-transparent text-zinc-500 hover:text-zinc-900 hover:bg-zinc-50'
            }`}>
              <span className="flex items-center justify-center gap-2"><Search className="w-4 h-4" /> 知识库检索</span>
            </TabsTrigger>
            <TabsTrigger value="runs" className={`flex-1 sm:flex-none px-8 py-4 font-bold uppercase tracking-widest text-sm transition-all outline-none border-b-4 rounded-none bg-transparent ${
              activeTab === 'runs'
                ? 'border-primary text-primary bg-primary/5'
                : 'border-transparent text-zinc-500 hover:text-zinc-900 hover:bg-zinc-50'
            }`}>
              <span className="flex items-center justify-center gap-2"><MessageSquare className="w-4 h-4" /> Run 历史</span>
            </TabsTrigger>
            <TabsTrigger value="chat" className={`flex-1 sm:flex-none px-8 py-4 font-bold uppercase tracking-widest text-sm transition-all outline-none border-b-4 rounded-none bg-transparent ${
              activeTab === 'chat'
                ? 'border-primary text-primary bg-primary/5'
                : 'border-transparent text-zinc-500 hover:text-zinc-900 hover:bg-zinc-50'
            }`}>
              <span className="flex items-center justify-center gap-2"><MessageSquare className="w-4 h-4" /> 问答</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="papers" className="mt-8 space-y-6 outline-none animate-in fade-in slide-in-from-bottom-4 duration-500">
            <KnowledgePapersPanel papers={papers} loading={papersLoading} onImport={() => setImportDialogOpen(true)} />
          </TabsContent>

          <TabsContent value="import-status" className="mt-8 outline-none animate-in fade-in slide-in-from-bottom-4 duration-500">
            <KnowledgeImportPanel
              importJobs={importJobs}
              onJobComplete={() => {
                void Promise.all([
                  loadImportJobs({ silent: true }),
                  loadPapers({ silent: true }),
                  loadKnowledgeBase({ silent: true }),
                  reloadRuns(),
                ]);
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
            <KnowledgeRunHistoryPanel runs={runs} loading={loadingRuns} onOpenRun={(runId) => navigate(`/chat?sessionId=${runId}&kbId=${kb.id}`)} />
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
