import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router';
import {
  ArrowLeft,
  Database,
  Library,
  Clock3,
  Search,
  MessageSquare,
  UploadCloud,
  Loader2,
  PanelRightClose,
  PanelRightOpen,
} from 'lucide-react';
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
import { buildFreshChatHref } from '@/features/chat/chatHandoff';
import { formatEmbeddingModelLabel, formatParseEngineLabel } from '@/config/modelRuntime';
import { getKnowledgeBaseDisplayMetadata } from '@/app/lib/knowledgeBaseDisplay';
import { WorkspaceShell } from '@/app/components/layout/WorkspaceShell';
import { ScrollArea } from '@/app/components/ui/scroll-area';
import { Button } from '@/app/components/ui/button';
import { KnowledgeWorkspaceInspector } from '@/features/kb/components/KnowledgeWorkspaceInspector';

export function KnowledgeWorkspaceShell() {
  const navigate = useNavigate();
  const [showInspector, setShowInspector] = useState(false);
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
    leading: false,
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
  const kbDisplay = useMemo(
    () => (kb ? getKnowledgeBaseDisplayMetadata(kb) : null),
    [kb],
  );

  if (loadingKB) {
    return (
      <div className="editorial-app-shell relative min-h-screen bg-background">
        <PaperTexture />
        <UnifiedLoadingState fullScreen={true} label="正在加载知识库..." />
      </div>
    );
  }

  if (!kb || !kbId) {
    return (
      <div className="editorial-app-shell relative min-h-screen bg-background">
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
    <div className="editorial-app-shell relative min-h-screen bg-background">
      <PaperTexture />
      <div className="relative z-10 h-[calc(100vh-5rem)] min-h-[720px] px-4 pb-6 pt-4 md:px-6">
        <WorkspaceShell
          layoutId="knowledge-workspace"
          sidebar={(
            <div className="flex h-full min-h-0 flex-col bg-stone-50/80">
              <div className="border-b border-border/50 px-5 py-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="text-[10px] font-bold uppercase tracking-[0.22em] text-muted-foreground">Knowledge Base</div>
                    <div className="mt-1 font-serif text-lg font-semibold text-foreground">
                      {kbDisplay?.displayName ?? kb.name}
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="hidden lg:inline-flex"
                    onClick={() => setShowInspector((value) => !value)}
                  >
                    {showInspector ? <PanelRightClose className="h-4 w-4" /> : <PanelRightOpen className="h-4 w-4" />}
                    {showInspector ? '收起' : '侧注'}
                  </Button>
                </div>
                <div className="mt-3 flex flex-wrap gap-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                  <span className="flex items-center gap-1.5 rounded-full border border-border/60 bg-paper-1 px-2.5 py-1">
                    <Database className="h-3.5 w-3.5" />
                    {formatEmbeddingModelLabel(kb.embeddingModel)}
                  </span>
                  <span className="rounded-full border border-primary/20 bg-primary/10 px-2.5 py-1 text-primary">
                    {formatParseEngineLabel(kb.parseEngine)}
                  </span>
                </div>
              </div>

              <ScrollArea className="flex-1">
                <div className="flex flex-col gap-4 p-4">
                  <div className="rounded-2xl border border-border/60 bg-paper-1 p-4">
                    <Link
                      to="/knowledge-bases"
                      className="mb-3 inline-flex items-center gap-2 text-xs font-bold uppercase tracking-[0.16em] text-muted-foreground transition-colors hover:text-primary"
                    >
                      <ArrowLeft className="w-4 h-4" />
                      返回知识库列表
                    </Link>
                    <div className="space-y-2">
                      <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground">Workspace Stats</div>
                      <div className="grid gap-2 text-sm text-foreground/85">
                        <div className="flex items-center justify-between rounded-xl border border-border/60 bg-background/85 px-3 py-2">
                          <span>{kb.paperCount} 篇论文</span>
                          <Library className="h-4 w-4 text-muted-foreground" />
                        </div>
                        <div className="flex items-center justify-between rounded-xl border border-border/60 bg-background/85 px-3 py-2">
                          <span>{kb.chunkCount} 个切片</span>
                          <Search className="h-4 w-4 text-muted-foreground" />
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="rounded-2xl border border-border/60 bg-card p-4">
                    <div className="mb-3 text-[10px] font-bold uppercase tracking-[0.22em] text-muted-foreground">Quick Actions</div>
                    <div className="space-y-2">
                      <Button className="w-full justify-start" variant="outline" onClick={() => syncTab('uploads')}>
                        <UploadCloud className="h-4 w-4" />
                        上传工作台
                      </Button>
                      <Button className="w-full justify-start" variant="outline" onClick={() => setImportDialogOpen(true)}>
                        <UploadCloud className="h-4 w-4" />
                        导入来源
                      </Button>
                      <Button className="w-full justify-start" onClick={() => navigate(buildFreshChatHref({ kbId: kb.id }))}>
                        <MessageSquare className="h-4 w-4" />
                        对整个知识库提问
                      </Button>
                    </div>
                  </div>

                  <div className="rounded-2xl border border-border/60 bg-card p-4">
                    <div className="mb-3 text-[10px] font-bold uppercase tracking-[0.22em] text-muted-foreground">工作流摘要</div>
                    <p className="text-xs leading-relaxed text-muted-foreground">
                      从论文导入、索引、检索到综述与问答的详细就绪状态，统一收口在右侧 inspector 中查看，避免主工作区重复堆叠状态卡片。
                    </p>
                  </div>
                </div>
              </ScrollArea>
            </div>
          )}
          main={(
            <div className="flex h-full min-h-0 flex-col bg-paper-1">
              <div className="border-b border-border/60 px-5 py-4">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <div className="text-[10px] font-bold uppercase tracking-[0.22em] text-muted-foreground">Knowledge Workspace</div>
                    <h1 className="mt-1 font-serif text-2xl font-semibold tracking-tight text-foreground">
                      {kbDisplay?.displayName ?? kb.name}
                    </h1>
                    <p className="mt-1 text-xs text-muted-foreground">{kbId}</p>
                  </div>
                  {!showInspector ? (
                    <Button
                      variant="outline"
                      size="sm"
                      className="hidden lg:inline-flex"
                      onClick={() => setShowInspector(true)}
                    >
                      <PanelRightOpen className="h-4 w-4" />
                      展开侧注
                    </Button>
                  ) : null}
                </div>
              </div>

              <Tabs value={activeTab} onValueChange={syncTab} className="flex min-h-0 flex-1 flex-col">
                <div className="border-b border-border/80 px-5">
                  <TabsList className="flex h-auto w-full flex-wrap justify-start gap-0 bg-transparent p-0">
                    <TabsTrigger value="papers" onClick={() => syncTab('papers')} className={`flex-1 sm:flex-none px-6 py-4 font-bold uppercase tracking-widest text-sm transition-all outline-none border-b-4 rounded-none bg-transparent ${
                      activeTab === 'papers'
                        ? 'border-primary text-foreground bg-transparent'
                        : 'border-transparent text-muted-foreground hover:text-foreground hover:bg-primary/[0.04]'
                    }`}>
                      <span className="flex items-center justify-center gap-2"><Library className="w-4 h-4" /> 论文列表</span>
                    </TabsTrigger>
                    <TabsTrigger value="import-status" onClick={() => syncTab('import-status')} className={`flex-1 sm:flex-none px-6 py-4 font-bold uppercase tracking-widest text-sm transition-all outline-none border-b-4 rounded-none bg-transparent ${
                      activeTab === 'import-status'
                        ? 'border-primary text-foreground bg-transparent'
                        : 'border-transparent text-muted-foreground hover:text-foreground hover:bg-primary/[0.04]'
                    }`}>
                      <span className="flex items-center justify-center gap-2"><Clock3 className="w-4 h-4" /> 导入状态</span>
                    </TabsTrigger>
                    <TabsTrigger value="uploads" onClick={() => syncTab('uploads')} className={`flex-1 sm:flex-none px-6 py-4 font-bold uppercase tracking-widest text-sm transition-all outline-none border-b-4 rounded-none bg-transparent ${
                      activeTab === 'uploads'
                        ? 'border-primary text-foreground bg-transparent'
                        : 'border-transparent text-muted-foreground hover:text-foreground hover:bg-primary/[0.04]'
                    }`}>
                      <span className="flex items-center justify-center gap-2"><UploadCloud className="w-4 h-4" /> 上传工作台</span>
                    </TabsTrigger>
                    <TabsTrigger value="search" onClick={() => syncTab('search')} className={`flex-1 sm:flex-none px-6 py-4 font-bold uppercase tracking-widest text-sm transition-all outline-none border-b-4 rounded-none bg-transparent ${
                      activeTab === 'search'
                        ? 'border-primary text-foreground bg-transparent'
                        : 'border-transparent text-muted-foreground hover:text-foreground hover:bg-primary/[0.04]'
                    }`}>
                      <span className="flex items-center justify-center gap-2"><Search className="w-4 h-4" /> 知识库检索</span>
                    </TabsTrigger>
                    <TabsTrigger value="runs" onClick={() => syncTab('runs')} className={`flex-1 sm:flex-none px-6 py-4 font-bold uppercase tracking-widest text-sm transition-all outline-none border-b-4 rounded-none bg-transparent ${
                      activeTab === 'runs'
                        ? 'border-primary text-foreground bg-transparent'
                        : 'border-transparent text-muted-foreground hover:text-foreground hover:bg-primary/[0.04]'
                    }`}>
                      <span className="flex items-center justify-center gap-2"><MessageSquare className="w-4 h-4" /> 运行记录</span>
                    </TabsTrigger>
                    <TabsTrigger value="review" onClick={() => syncTab('review')} className={`flex-1 sm:flex-none px-6 py-4 font-bold uppercase tracking-widest text-sm transition-all outline-none border-b-4 rounded-none bg-transparent ${
                      activeTab === 'review'
                        ? 'border-primary text-foreground bg-transparent'
                        : 'border-transparent text-muted-foreground hover:text-foreground hover:bg-primary/[0.04]'
                    }`}>
                      <span className="flex items-center justify-center gap-2"><MessageSquare className="w-4 h-4" /> 综述草稿</span>
                    </TabsTrigger>
                    <TabsTrigger value="chat" onClick={() => syncTab('chat')} className={`flex-1 sm:flex-none px-6 py-4 font-bold uppercase tracking-widest text-sm transition-all outline-none border-b-4 rounded-none bg-transparent ${
                      activeTab === 'chat'
                        ? 'border-primary text-foreground bg-transparent'
                        : 'border-transparent text-muted-foreground hover:text-foreground hover:bg-primary/[0.04]'
                    }`}>
                      <span className="flex items-center justify-center gap-2"><MessageSquare className="w-4 h-4" /> 问答</span>
                    </TabsTrigger>
                  </TabsList>
                </div>

                <div className="min-h-0 flex-1 overflow-y-auto px-5 py-6">
                  <TabsContent value="papers" className="space-y-6 outline-none animate-in fade-in slide-in-from-bottom-4 duration-500">
                    <KnowledgePapersPanel
                      papers={papers}
                      loading={papersLoading}
                      highlightedPaperId={importedPaperId}
                      onImport={() => setImportDialogOpen(true)}
                    />
                  </TabsContent>

                  <TabsContent value="import-status" className="outline-none animate-in fade-in slide-in-from-bottom-4 duration-500">
                    <KnowledgeImportPanel
                      importJobs={importJobs}
                      onJobComplete={() => {
                        void refreshImportStatus({ refreshDerivedOnCompleted: true });
                      }}
                    />
                  </TabsContent>

                  <TabsContent value="uploads" className="outline-none animate-in fade-in slide-in-from-bottom-4 duration-500">
                    <UploadWorkspace
                      knowledgeBaseId={kb.id}
                      onQueueComplete={() => {
                        void refreshImportStatus({ refreshDerivedOnCompleted: true });
                      }}
                    />
                  </TabsContent>

                  <TabsContent value="search" className="outline-none animate-in fade-in slide-in-from-bottom-4 duration-500">
                    <KnowledgeEvidencePanel
                      searchQuery={search.searchDraft}
                      isSearching={search.isSearching}
                      results={search.results}
                      papersEmpty={!papersLoading && papers.length === 0}
                      onSearchQueryChange={search.setSearchDraft}
                      onSearchSubmit={(query) => void search.search(query)}
                      onOpenPaper={(paperId, page, sourceChunkId) => {
                        const params = new URLSearchParams({
                          page: String(page || 1),
                          source: 'evidence',
                        });
                        if (sourceChunkId) {
                          params.set('source_id', sourceChunkId);
                        }
                        navigate(`/read/${paperId}?${params.toString()}`);
                      }}
                    />
                  </TabsContent>

                  <TabsContent value="runs" className="outline-none animate-in fade-in slide-in-from-bottom-4 duration-500">
                    <KnowledgeRunHistoryPanel
                      runs={runs}
                      loading={loadingRuns}
                      onOpenRun={(runId) => navigate(`/knowledge-bases/${kb.id}?tab=review&runId=${runId}`)}
                    />
                  </TabsContent>

                  <TabsContent value="review" className="outline-none animate-in fade-in slide-in-from-bottom-4 duration-500">
                    <KnowledgeReviewPanel kbId={kb.id} papers={papers} onRunChanged={() => void reloadRuns()} />
                  </TabsContent>

                  <TabsContent value="chat" className="outline-none animate-in fade-in slide-in-from-bottom-4 duration-500">
                    <KnowledgeQuickAskPanel kbId={kb.id} onEnterChat={() => navigate(buildFreshChatHref({ kbId: kb.id }))} />
                  </TabsContent>
                </div>
              </Tabs>
            </div>
          )}
          inspector={
            showInspector ? (
              <KnowledgeWorkspaceInspector
                readinessItems={readinessItems}
                onRefresh={() => refreshAll({ silent: true })}
                onClose={() => setShowInspector(false)}
                onNavigate={(href) => navigate(href)}
              />
            ) : undefined
          }
        />
      </div>

      <ImportDialog
        open={isImportDialogOpen}
        onOpenChange={setImportDialogOpen}
        knowledgeBaseId={kb.id}
        knowledgeBaseName={kbDisplay?.displayName ?? kb.name}
        onImportComplete={() => {
          void handleImportCompleted();
          toast.success('导入任务已提交');
        }}
      />
    </div>
  );
}
