import { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate, useParams, useSearchParams, Link } from "react-router";
import {
  ArrowLeft,
  Search,
  UploadCloud,
  FileText,
  MessageSquare,
  Database,
  Loader2,
  Clock3,
  Library,
} from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/app/components/ui/tabs";
import { ImportDialog } from "@/app/components/ImportDialog";
import { ImportQueueList } from "@/app/components/ImportQueueList";
import { PaperTexture } from "@/app/components/PaperTexture";
import { Button } from "@/app/components/ui/button";
import { PaperListItem } from "@/app/components/PaperListItem";
import { ImportJob, importApi } from "@/services/importApi";
import {
  kbApi,
  KnowledgeBase,
  KBPaperListItem,
  KBSearchResult,
} from "@/services/kbApi";
import { toast } from "sonner";
import { useImportJobsPolling } from '@/features/kb/hooks/useImportJobsPolling';

// LEGACY FREEZE (PR10):
// - This component is in migration mode.
// - Do not add new business logic here.
// - New state/workflow changes must land in features/kb/hooks and workspace store.

export function KnowledgeBaseDetailLegacy() {
  const navigate = useNavigate();
  const { id: kbId } = useParams<{ id: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState(
    searchParams.get("tab") || "papers"
  );
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);

  const [kb, setKB] = useState<KnowledgeBase | null>(null);
  const [loadingKB, setLoadingKB] = useState(true);
  const [papers, setPapers] = useState<KBPaperListItem[]>([]);
  const [papersLoading, setPapersLoading] = useState(false);
  const [importJobs, setImportJobs] = useState<ImportJob[]>([]);
  const [importJobsLoading, setImportJobsLoading] = useState(false);
  const previousImportJobStatus = useRef<Record<string, string>>({});

  const [searchQuery, setSearchQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState<KBSearchResult[] | null>(null);

  const loadKnowledgeBase = useCallback(async (options?: { silent?: boolean }) => {
    if (!kbId) return;

    if (!options?.silent) {
      setLoadingKB(true);
    }
    try {
      const res = await kbApi.get(kbId);
      setKB(res);
    } catch (err: any) {
      if (!options?.silent) {
        toast.error(err.message || "网络错误");
      }
    } finally {
      if (!options?.silent) {
        setLoadingKB(false);
      }
    }
  }, [kbId]);

  const loadPapers = useCallback(async (options?: { silent?: boolean }) => {
    if (!kbId) return;

    if (!options?.silent) {
      setPapersLoading(true);
    }
    try {
      const response = await kbApi.listPapers(kbId);
      setPapers(response.papers || []);
    } catch (err: any) {
      if (!options?.silent) {
        toast.error(err.message || "加载知识库论文失败");
      }
    } finally {
      if (!options?.silent) {
        setPapersLoading(false);
      }
    }
  }, [kbId]);

  const loadImportJobs = useCallback(async (options?: { silent?: boolean }) => {
    if (!kbId) return;
    if (!options?.silent) setImportJobsLoading(true);
    try {
      const response = await importApi.list(kbId, { limit: 50 });
      if (response.success && response.data) {
        setImportJobs(response.data.jobs);
      }
    } catch (err) {
      // silent fail - ImportQueueList at page bottom handles errors
    } finally {
      if (!options?.silent) setImportJobsLoading(false);
    }
  }, [kbId]);

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

  useEffect(() => {
    void loadImportJobs();
  }, [loadImportJobs]);

  useEffect(() => {
    const hasNewlyCompletedJob = importJobs.some((job) => {
      const previousStatus = previousImportJobStatus.current[job.importJobId];
      return job.status === "completed" && previousStatus !== "completed";
    });

    previousImportJobStatus.current = importJobs.reduce<Record<string, string>>(
      (acc, job) => ({
        ...acc,
        [job.importJobId]: job.status,
      }),
      {}
    );

    if (hasNewlyCompletedJob) {
      void Promise.all([
        loadPapers({ silent: true }),
        loadKnowledgeBase({ silent: true }),
      ]);
    }
  }, [importJobs, loadKnowledgeBase, loadPapers]);

  const refreshKnowledgeBaseWorkspace = useCallback(async (options?: { silent?: boolean }) => {
    await Promise.all([
      loadKnowledgeBase(options),
      loadPapers(options),
      loadImportJobs(options),  // D-02: unified polling
    ]);
  }, [loadKnowledgeBase, loadPapers, loadImportJobs]);

  useEffect(() => {
    void refreshKnowledgeBaseWorkspace();
  }, [refreshKnowledgeBaseWorkspace]);

  const handleTabChange = (tab: string) => {
    setActiveTab(tab);
    setSearchParams({ tab });
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim() || !kbId) return;

    setIsSearching(true);
    try {
      const res = await kbApi.search(kbId, searchQuery);
      setResults(res.results || []);
    } catch (err: any) {
      toast.error(err.message || "搜索失败");
    } finally {
      setIsSearching(false);
    }
  };

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

  if (!kb) {
    return (
      <div className="relative min-h-screen bg-background">
        <PaperTexture />
        <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
          <div className="text-zinc-500 font-medium">知识库不存在或已删除</div>
          <button
            onClick={() => navigate("/knowledge-bases")}
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
              onClick={(e) => {
                e.preventDefault();
                navigate("/knowledge-bases");
              }}
            >
              <ArrowLeft className="w-4 h-4" />
              返回知识库列表
            </Link>
            <div className="flex items-center gap-4">
              <h1 className="text-4xl md:text-5xl font-black font-serif uppercase tracking-tight text-zinc-900 leading-none">
                {kb.name.split(" ")[0]}{" "}
                <span className="text-primary">
                  {kb.name.split(" ").slice(1).join(" ") || kb.name}
                </span>
              </h1>
              <span className="bg-zinc-100 border border-zinc-300 px-3 py-1 font-mono text-sm text-zinc-600 shadow-[2px_2px_0px_0px_rgba(24,24,27,0.2)]">
                {kbId}
              </span>
            </div>
            <div className="flex flex-wrap gap-4 text-sm font-bold uppercase tracking-wider text-zinc-500 pt-2">
              <span className="flex items-center gap-2">
                <Database className="w-4 h-4" /> {kb.embeddingModel} Model
              </span>
              <span className="flex items-center gap-2 text-primary">
                ★ {kb.parseEngine} Engine
              </span>
              <span>{kb.paperCount} Papers</span>
              <span>{kb.chunkCount} Chunks</span>
              {kb.entityCount > 0 ? (
                <span>{kb.entityCount} Entities</span>
              ) : (
                <span>Graph Pending</span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-4 shrink-0">
            <button
              onClick={() => setIsImportModalOpen(true)}
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

        <Tabs value={activeTab} onValueChange={handleTabChange} className="w-full">
          <TabsList className="flex flex-wrap border-b-2 border-zinc-200 bg-transparent h-auto p-0 gap-0 w-full justify-start">
            <TabsTrigger
              value="papers"
              className={`flex-1 sm:flex-none px-8 py-4 font-bold uppercase tracking-widest text-sm transition-all outline-none border-b-4 rounded-none bg-transparent ${
                activeTab === "papers"
                  ? "border-primary text-primary bg-primary/5"
                  : "border-transparent text-zinc-500 hover:text-zinc-900 hover:bg-zinc-50"
              }`}
            >
              <span className="flex items-center justify-center gap-2">
                <Library className="w-4 h-4" /> 论文列表
              </span>
            </TabsTrigger>
            <TabsTrigger
              value="import-status"
              className={`flex-1 sm:flex-none px-8 py-4 font-bold uppercase tracking-widest text-sm transition-all outline-none border-b-4 rounded-none bg-transparent ${
                activeTab === "import-status"
                  ? "border-primary text-primary bg-primary/5"
                  : "border-transparent text-zinc-500 hover:text-zinc-900 hover:bg-zinc-50"
              }`}
            >
              <span className="flex items-center justify-center gap-2">
                <Clock3 className="w-4 h-4" /> 导入状态
              </span>
            </TabsTrigger>
            <TabsTrigger
              value="search"
              className={`flex-1 sm:flex-none px-8 py-4 font-bold uppercase tracking-widest text-sm transition-all outline-none border-b-4 rounded-none bg-transparent ${
                activeTab === "search"
                  ? "border-primary text-primary bg-primary/5"
                  : "border-transparent text-zinc-500 hover:text-zinc-900 hover:bg-zinc-50"
              }`}
            >
              <span className="flex items-center justify-center gap-2">
                <Search className="w-4 h-4" /> 知识库检索
              </span>
            </TabsTrigger>
            <TabsTrigger
              value="chat"
              className={`flex-1 sm:flex-none px-8 py-4 font-bold uppercase tracking-widest text-sm transition-all outline-none border-b-4 rounded-none bg-transparent ${
                activeTab === "chat"
                  ? "border-primary text-primary bg-primary/5"
                  : "border-transparent text-zinc-500 hover:text-zinc-900 hover:bg-zinc-50"
              }`}
            >
              <span className="flex items-center justify-center gap-2">
                <MessageSquare className="w-4 h-4" /> 问答
              </span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="papers" className="mt-8 space-y-6 outline-none animate-in fade-in slide-in-from-bottom-4 duration-500">
            {papersLoading ? (
              <div className="flex items-center justify-center py-16">
                <Loader2 className="w-6 h-6 animate-spin text-primary" />
              </div>
            ) : papers.length === 0 ? (
              <div className="bg-white border-2 border-zinc-900 p-10 text-center space-y-4 shadow-[8px_8px_0px_0px_rgba(24,24,27,1)]">
                <div className="text-zinc-600 font-medium">当前知识库还没有论文</div>
                <Button onClick={() => setIsImportModalOpen(true)}>导入第一篇论文</Button>
              </div>
            ) : (
              <div className="space-y-4">
                {papers.map((paper) => (
                  <PaperListItem
                    key={paper.id}
                    id={paper.id}
                    title={paper.title}
                    authors={paper.authors?.join("、") || "未知作者"}
                    year={paper.year ? String(paper.year) : "未知年份"}
                    venue={paper.venue || "未标注来源"}
                    chunkCount={paper.chunkCount || 0}
                    parseStatus={
                      ["pending", "processing", "completed", "failed"].includes(paper.status)
                        ? (paper.status as "pending" | "processing" | "completed" | "failed")
                        : "pending"
                    }
                    entityCount={paper.entityCount || 0}
                    onRead={() => navigate(`/read/${paper.id}`)}
                    onNotes={() => navigate(`/notes?paperId=${paper.id}`)}
                    onQuery={(paperId) => navigate(`/chat?paperId=${paperId}`)}
                  />
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="import-status" className="mt-8 outline-none animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="bg-white border-2 border-zinc-900 shadow-[8px_8px_0px_0px_rgba(24,24,27,1)] p-6 min-h-[420px] flex flex-col">
              <div className="mb-4">
                <h3 className="font-serif text-xl font-semibold">论文导入与处理记录</h3>
                <p className="text-sm text-zinc-500 mt-1">查看导入中的任务和历史处理记录</p>
              </div>
              <ImportQueueList
                jobs={importJobs}
                initiallyExpanded={true}
                onJobComplete={() => {
                  void Promise.all([
                    loadImportJobs({ silent: true }),
                    loadPapers({ silent: true }),
                    loadKnowledgeBase({ silent: true }),
                  ]);
                }}
              />
            </div>
          </TabsContent>

          <TabsContent value="search" className="mt-8 space-y-8 outline-none animate-in fade-in slide-in-from-bottom-4 duration-500">
            <form onSubmit={handleSearch} className="relative max-w-3xl">
              <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                <Search className="h-6 w-6 text-zinc-400" />
              </div>
              <input
                type="text"
                className="block w-full pl-12 pr-32 py-5 text-lg border-2 border-zinc-900 font-medium placeholder:text-zinc-400 focus:outline-none focus:ring-0 focus:border-primary shadow-[6px_6px_0px_0px_rgba(24,24,27,1)] transition-colors bg-white"
                placeholder="输入您的问题..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
              <button
                type="submit"
                disabled={isSearching || !searchQuery.trim()}
                className="absolute right-2 top-2 bottom-2 bg-primary hover:bg-zinc-900 text-white px-6 font-bold uppercase tracking-wider transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {isSearching ? <Loader2 className="w-5 h-5 animate-spin" /> : "检索"}
              </button>
            </form>

            {!papersLoading && papers.length === 0 ? (
              <div className="bg-white border-2 border-zinc-900 p-8 text-center text-zinc-600 font-medium shadow-[8px_8px_0px_0px_rgba(24,24,27,1)]">
                请先向知识库导入论文，再开始检索。
              </div>
            ) : results && results.length > 0 ? (
              <div className="space-y-6 max-w-4xl">
                <div className="flex items-center gap-4 mb-8">
                  <div className="h-px bg-zinc-300 flex-1"></div>
                  <span className="text-zinc-500 font-bold uppercase tracking-widest text-sm px-4">
                    检索到 {results.length} 个相关片段
                  </span>
                  <div className="h-px bg-zinc-300 flex-1"></div>
                </div>

                {results.map((result) => (
                  <div
                    key={result.id}
                    className="bg-white border-2 border-zinc-200 p-6 relative hover:border-zinc-400 transition-colors group cursor-pointer"
                    onClick={() => {
                      const page = result.page || 1;
                      navigate(`/read/${result.paperId}?page=${page}`);
                    }}
                  >
                    <div className="absolute -left-2 -top-2 bg-orange-100 text-orange-800 border-2 border-orange-200 font-mono text-xs px-2 py-1 font-bold shadow-sm">
                      相关度: {(result.score * 100).toFixed(1)}%
                    </div>
                    <p className="text-lg text-zinc-800 mt-4 leading-relaxed font-serif">
                      "...{result.content}..."
                    </p>
                    <div className="mt-6 flex items-center gap-2 text-sm font-medium text-zinc-500 bg-zinc-50 p-3 border border-zinc-100">
                      <FileText className="w-4 h-4 text-zinc-400" />
                      <span className="truncate">{result.paperTitle || result.paperId}</span>
                      {result.page && <span className="text-primary">第{result.page}页</span>}
                    </div>
                  </div>
                ))}
              </div>
            ) : results && results.length === 0 ? (
              <div className="bg-white border-2 border-zinc-900 p-8 text-center text-zinc-600 font-medium shadow-[8px_8px_0px_0px_rgba(24,24,27,1)]">
                没有检索到相关结果，请尝试其他问题。
              </div>
            ) : null}
          </TabsContent>

          <TabsContent value="chat" className="mt-8 outline-none animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-4xl">
            <div className="bg-white border-2 border-zinc-900 shadow-[8px_8px_0px_0px_rgba(24,24,27,1)] p-8 space-y-4">
              <h3 className="font-serif text-2xl font-semibold">统一问答入口</h3>
              <p className="text-zinc-600 leading-relaxed">
                当前知识库问答已统一到 Chat 页面。进入后可在“快速问答 (RAG)”与“深度分析 (Agent)”之间切换，
                并保持当前知识库作用域。
              </p>
              <div className="pt-2">
                <Button onClick={() => navigate(`/chat?kbId=${kb.id}`)}>
                  进入 Chat（全知识库作用域）
                </Button>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </div>

      <ImportDialog
        open={isImportModalOpen}
        onOpenChange={setIsImportModalOpen}
        knowledgeBaseId={kb.id}
        knowledgeBaseName={kb.name}
        onImportComplete={refreshKnowledgeBaseWorkspace}
      />
    </div>
  );
}
