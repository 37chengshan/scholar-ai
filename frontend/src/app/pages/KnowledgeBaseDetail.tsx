import { useState, useEffect, useCallback } from "react";
import { useNavigate, useParams, useSearchParams, Link } from "react-router";
import {
  ArrowLeft,
  Search,
  UploadCloud,
  FileText,
  MessageSquare,
  Send,
  Sparkles,
  Database,
  Loader2,
  Clock3,
  Library,
} from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { ImportDialog } from "../components/ImportDialog";
import { ImportQueueList } from "../components/ImportQueueList";
import { PaperTexture } from "../components/PaperTexture";
import { Button } from "../components/ui/button";
import { PaperListItem } from "../components/PaperListItem";
import { UploadHistoryList } from "@/components/upload/UploadHistoryList";
import { uploadHistoryApi } from "@/services/uploadHistoryApi";
import {
  kbApi,
  KnowledgeBase,
  KBPaperListItem,
  KBSearchResult,
  KBUploadHistoryRecord,
} from "@/services/kbApi";
import { toast } from "sonner";

export function KnowledgeBaseDetail() {
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
  const [uploadRecords, setUploadRecords] = useState<KBUploadHistoryRecord[]>([]);
  const [uploadHistoryLoading, setUploadHistoryLoading] = useState(false);

  const [messages, setMessages] = useState<
    { role: string; content: string; citations?: any[]; isError?: boolean }[]
  >([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);

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
      if (res.success && res.data) {
        setKB(res.data);
      } else if (!options?.silent) {
        toast.error("获取知识库详情失败");
      }
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
      if (response.success && response.data) {
        setPapers(response.data.papers || []);
      } else if (!options?.silent) {
        toast.error("加载知识库论文失败");
      }
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

  const loadUploadHistory = useCallback(async (options?: { silent?: boolean }) => {
    if (!kbId) return;

    if (!options?.silent) {
      setUploadHistoryLoading(true);
    }
    try {
      const response = await kbApi.getUploadHistory(kbId, { limit: 20, offset: 0 });
      if (response.success && response.data) {
        setUploadRecords(response.data.records || []);
      } else if (!options?.silent) {
        toast.error("加载上传记录失败");
      }
    } catch (err: any) {
      if (!options?.silent) {
        toast.error(err.message || "加载上传记录失败");
      }
    } finally {
      if (!options?.silent) {
        setUploadHistoryLoading(false);
      }
    }
  }, [kbId]);

  const handleDeleteUploadRecord = useCallback(async (id: string) => {
    try {
      await uploadHistoryApi.delete(id);
      setUploadRecords((prev) => prev.filter((record) => record.id !== id));
      toast.success("上传记录已删除");
    } catch (err: any) {
      toast.error(err.message || "删除上传记录失败");
    }
  }, []);

  const refreshKnowledgeBaseWorkspace = useCallback(async (options?: { silent?: boolean }) => {
    await Promise.all([
      loadKnowledgeBase(options),
      loadPapers(options),
      loadUploadHistory(options),
    ]);
  }, [loadKnowledgeBase, loadPapers, loadUploadHistory]);

  useEffect(() => {
    if (!uploadRecords.some((record) => record.status === "PROCESSING")) {
      return;
    }

    const timer = window.setInterval(() => {
      void refreshKnowledgeBaseWorkspace({ silent: true });
    }, 2000);

    return () => window.clearInterval(timer);
  }, [uploadRecords, refreshKnowledgeBaseWorkspace]);

  useEffect(() => {
    void refreshKnowledgeBaseWorkspace();
  }, [refreshKnowledgeBaseWorkspace]);

  const handleTabChange = (tab: string) => {
    setActiveTab(tab);
    setSearchParams({ tab });
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !kbId) return;

    const userMessage = input.trim();
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setInput("");
    setIsTyping(true);

    try {
      const response = await kbApi.query(kbId, userMessage);

      if (response.success && response.data) {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: response.data.answer || "抱歉，我无法处理您的请求。",
            citations: response.data.citations,
          },
        ]);
      } else {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: "抱歉，知识库问答暂时不可用，请稍后再试。",
            isError: true,
          },
        ]);
        toast.error("问答请求失败");
      }
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `错误: ${err.message || "网络请求失败"}`,
          isError: true,
        },
      ]);
      toast.error(err.message || "问答失败");
    } finally {
      setIsTyping(false);
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim() || !kbId) return;

    setIsSearching(true);
    try {
      const res = await kbApi.search(kbId, searchQuery);
      if (res.success && res.data) {
        setResults(res.data.results);
      } else {
        toast.error("搜索失败");
      }
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
              value="uploads"
              className={`flex-1 sm:flex-none px-8 py-4 font-bold uppercase tracking-widest text-sm transition-all outline-none border-b-4 rounded-none bg-transparent ${
                activeTab === "uploads"
                  ? "border-primary text-primary bg-primary/5"
                  : "border-transparent text-zinc-500 hover:text-zinc-900 hover:bg-zinc-50"
              }`}
            >
              <span className="flex items-center justify-center gap-2">
                <Clock3 className="w-4 h-4" /> 上传记录
              </span>
            </TabsTrigger>
            <TabsTrigger
              value="retrieval"
              className={`flex-1 sm:flex-none px-8 py-4 font-bold uppercase tracking-widest text-sm transition-all outline-none border-b-4 rounded-none bg-transparent ${
                activeTab === "retrieval"
                  ? "border-primary text-primary bg-primary/5"
                  : "border-transparent text-zinc-500 hover:text-zinc-900 hover:bg-zinc-50"
              }`}
            >
              <span className="flex items-center justify-center gap-2">
                <Search className="w-4 h-4" /> 知识库检索
              </span>
            </TabsTrigger>
            <TabsTrigger
              value="qa"
              className={`flex-1 sm:flex-none px-8 py-4 font-bold uppercase tracking-widest text-sm transition-all outline-none border-b-4 rounded-none bg-transparent ${
                activeTab === "qa"
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
                  />
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="uploads" className="mt-8 outline-none animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="bg-white border-2 border-zinc-900 shadow-[8px_8px_0px_0px_rgba(24,24,27,1)] p-6 min-h-[420px] flex flex-col">
              <div className="mb-4">
                <h3 className="font-serif text-xl font-semibold">知识库上传记录</h3>
                <p className="text-sm text-zinc-500 mt-1">查看导入历史和真实处理状态</p>
              </div>
              <UploadHistoryList
                records={uploadRecords}
                isLoading={uploadHistoryLoading}
                onDelete={handleDeleteUploadRecord}
              />
            </div>
          </TabsContent>

          <TabsContent value="retrieval" className="mt-8 space-y-8 outline-none animate-in fade-in slide-in-from-bottom-4 duration-500">
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

          <TabsContent value="qa" className="mt-8 outline-none animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-4xl">
            <div className="bg-white border-2 border-zinc-900 shadow-[8px_8px_0px_0px_rgba(24,24,27,1)] flex flex-col h-[600px]">
              <div className="flex-1 overflow-y-auto p-6 space-y-6">
                {messages.length === 0 && !isTyping && (
                  <div className="text-center text-zinc-500 py-12 font-medium">
                    请输入问题，针对当前知识库发起问答。
                  </div>
                )}
                {messages.map((msg, i) => (
                  <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                    <div
                      className={`max-w-[80%] p-5 text-base md:text-lg ${
                        msg.role === "user"
                          ? "bg-zinc-900 text-white font-medium ml-auto"
                          : "bg-primary/5 text-zinc-900 border-2 border-primary/20 font-serif leading-relaxed"
                      }`}
                    >
                      {msg.role === "assistant" && (
                        <div className="flex items-center gap-2 mb-3 text-primary font-sans text-xs font-bold uppercase tracking-wider">
                          <Sparkles className="w-4 h-4" /> Agent Output
                        </div>
                      )}
                      {msg.content}

                      {msg.role === "assistant" && msg.citations && msg.citations.length > 0 && (
                        <div className="mt-4 pt-3 border-t border-primary/20">
                          <div className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2">
                            引用来源 ({msg.citations.length})
                          </div>
                          <div className="space-y-2">
                            {msg.citations.map((citation: any, idx: number) => (
                              <div
                                key={idx}
                                className="flex items-center gap-2 text-xs cursor-pointer hover:text-primary transition-colors group"
                                onClick={() => {
                                  const page = citation.page || 1;
                                  const paperId = citation.paperId || citation.paper_id;
                                  if (!paperId) return;
                                  navigate(`/read/${paperId}?page=${page}`);
                                }}
                              >
                                <FileText className="w-3 h-3 text-muted-foreground" />
                                <span className="text-muted-foreground group-hover:text-primary">[{idx + 1}]</span>
                                <span className="truncate">{citation.paperTitle || citation.paperId || citation.paper_id}</span>
                                {citation.page && (
                                  <span className="text-primary font-bold">第{citation.page}页</span>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                {isTyping && (
                  <div className="flex justify-start">
                    <div className="bg-primary/5 text-primary border-2 border-primary/20 p-5 flex items-center gap-2">
                      <Loader2 className="w-5 h-5 animate-spin" />
                      <span className="font-bold uppercase tracking-widest text-xs">Synthesizing...</span>
                    </div>
                  </div>
                )}
              </div>

              <div className="border-t-2 border-zinc-900 p-4 bg-zinc-50">
                <form onSubmit={handleSendMessage} className="relative flex items-center">
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Ask a question about your knowledge base..."
                    className="w-full bg-white border-2 border-zinc-300 pl-4 pr-16 py-4 font-medium placeholder:text-zinc-400 focus:outline-none focus:border-secondary transition-colors"
                  />
                  <button
                    type="submit"
                    disabled={!input.trim() || isTyping}
                    className="absolute right-2 p-2 bg-primary hover:bg-primary/80 text-white transition-colors disabled:opacity-50 disabled:hover:bg-primary outline-none"
                  >
                    <Send className="w-5 h-5" />
                  </button>
                </form>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </div>

      {/* Import Queue List - embedded import history */}
      <div className="max-w-7xl mx-auto px-6 pb-8 relative z-10">
        <div className="bg-white border-2 border-zinc-900 shadow-[8px_8px_0px_0px_rgba(24,24,27,1)] p-6">
          <ImportQueueList kbId={kb.id} />
        </div>
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
