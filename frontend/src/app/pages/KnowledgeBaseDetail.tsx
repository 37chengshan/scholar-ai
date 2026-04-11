import { useState, useEffect } from "react";
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
} from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { ImportKnowledgeDialog } from "../components/ImportKnowledgeDialog";
import { PaperTexture } from "../components/PaperTexture";
import { kbApi, KnowledgeBase, KBSearchResult } from "@/services/kbApi";
import { toast } from "sonner";

export function KnowledgeBaseDetail() {
  const navigate = useNavigate();
  const { id: kbId } = useParams<{ id: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState(searchParams.get("tab") || "retrieval");
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);

  // KB State
  const [kb, setKB] = useState<KnowledgeBase | null>(null);
  const [loadingKB, setLoadingKB] = useState(true);

  // Q&A State (local messages, chat API handled separately)
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([
    { role: "assistant", content: "你好！我可以基于这个知识库回答问题。你想了解什么？" },
  ]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);

  // Retrieval State
  const [searchQuery, setSearchQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState<KBSearchResult[] | null>(null);

  // Fetch KB on mount
  useEffect(() => {
    if (kbId) {
      setLoadingKB(true);
      kbApi.get(kbId)
        .then(res => {
          if (res.success && res.data) {
            setKB(res.data);
          } else {
            toast.error('获取知识库详情失败');
          }
        })
        .catch(err => {
          toast.error(err.message || '网络错误');
        })
        .finally(() => {
          setLoadingKB(false);
        });
    }
  }, [kbId]);

  // Sync tab with URL
  const handleTabChange = (tab: string) => {
    setActiveTab(tab);
    setSearchParams({ tab });
  };

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    setMessages([...messages, { role: "user", content: input }]);
    setInput("");
    setIsTyping(true);

    // TODO: Implement KB chat API streaming
    setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "根据知识库内容分析，建议进一步探索相关主题。",
        },
      ]);
      setIsTyping(false);
    }, 1500);
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
        toast.error('搜索失败');
      }
    } catch (err: any) {
      toast.error(err.message || '搜索失败');
    } finally {
      setIsSearching(false);
    }
  };

  // Loading state
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

  // Error state (KB not found)
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
        {/* Header */}
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
                {kb.name.split(" ")[0]} <span className="text-primary">{kb.name.split(" ").slice(1).join(" ") || kb.name}</span>
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
              onClick={() => setIsImportModalOpen(true)}
              className="flex items-center gap-2 bg-zinc-900 hover:bg-primary text-white px-6 py-4 font-bold uppercase tracking-wide transition-all shadow-[4px_4px_0px_0px_rgba(24,24,27,0.5)] hover:shadow-[4px_4px_0px_0px_rgba(211,84,0,0.8)] hover:-translate-y-1 hover:-translate-x-1"
            >
              <UploadCloud className="w-5 h-5" />
              导入来源
            </button>
          </div>
        </div>

        {/* Main Content Area with Tabs */}
        <Tabs value={activeTab} onValueChange={handleTabChange} className="w-full">
          <TabsList className="flex border-b-2 border-zinc-200 bg-transparent h-auto p-0 gap-0 w-full justify-start">
            <TabsTrigger
              value="retrieval"
              className={`flex-1 sm:flex-none px-8 py-4 font-bold uppercase tracking-widest text-sm transition-all outline-none border-b-4 rounded-none bg-transparent data-[state=active]:bg-primary/5 ${
                activeTab === "retrieval"
                  ? "border-primary text-primary"
                  : "border-transparent text-zinc-500 hover:text-zinc-900 hover:bg-zinc-50"
              }`}
            >
              <span className="flex items-center justify-center gap-2">
                <Search className="w-4 h-4" /> Vector Search
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
                <MessageSquare className="w-4 w-4" /> Agentic Q&A
              </span>
            </TabsTrigger>
          </TabsList>

          <TabsContent
            value="retrieval"
            className="mt-8 space-y-8 outline-none animate-in fade-in slide-in-from-bottom-4 duration-500"
          >
            {/* Search Form */}
            <form onSubmit={handleSearch} className="relative max-w-3xl">
              <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                <Search className="h-6 w-6 text-zinc-400" />
              </div>
              <input
                type="text"
                className="block w-full pl-12 pr-32 py-5 text-lg border-2 border-zinc-900 font-medium placeholder:text-zinc-400 focus:outline-none focus:ring-0 focus:border-primary shadow-[6px_6px_0px_0px_rgba(24,24,27,1)] transition-colors bg-white"
                placeholder="Query vectorized chunks..."
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

            {/* Results List */}
            {results && (
              <div className="space-y-6 max-w-4xl">
                <div className="flex items-center gap-4 mb-8">
                  <div className="h-px bg-zinc-300 flex-1"></div>
                  <span className="text-zinc-500 font-bold uppercase tracking-widest text-sm px-4">
                    Top {results.length} Segments Retrieved
                  </span>
                  <div className="h-px bg-zinc-300 flex-1"></div>
                </div>

                {results.map((result) => (
                  <div
                    key={result.id}
                    className="bg-white border-2 border-zinc-200 p-6 relative hover:border-zinc-400 transition-colors group"
                  >
                    <div className="absolute -left-2 -top-2 bg-orange-100 text-orange-800 border-2 border-orange-200 font-mono text-xs px-2 py-1 font-bold shadow-sm">
                      Relevance: {(result.score * 100).toFixed(1)}%
                    </div>
                    <p className="text-lg text-zinc-800 mt-4 leading-relaxed font-serif">
                      "...{result.content}..."
                    </p>
                    <div className="mt-6 flex items-center gap-2 text-sm font-medium text-zinc-500 bg-zinc-50 p-3 border border-zinc-100">
                      <FileText className="w-4 h-4 text-zinc-400" />
                      <span className="truncate">{result.paperId}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent
            value="qa"
            className="mt-8 outline-none animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-4xl"
          >
            <div className="bg-white border-2 border-zinc-900 shadow-[8px_8px_0px_0px_rgba(24,24,27,1)] flex flex-col h-[600px]">
              {/* Chat History */}
              <div className="flex-1 overflow-y-auto p-6 space-y-6">
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

              {/* Chat Input */}
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

      {/* Import Dialog - uses existing ImportKnowledgeDialog component */}
      <ImportKnowledgeDialog
        open={isImportModalOpen}
        onOpenChange={setIsImportModalOpen}
        knowledgeBaseId={kb.id}
        knowledgeBaseName={kb.name}
      />
    </div>
  );
}