/**
 * Search Page
 *
 * Unified search across internal library and external sources (arXiv, Semantic Scholar)
 * Plus author search functionality (Phase 23)
 *
 * Features:
 * - 300ms debounce search (D-11)
 * - Internal papers from user's library
 * - External papers from arXiv and Semantic Scholar
 * - Author search with hIndex/citation metrics (Phase 23)
 * - Paper autocomplete suggestions (Phase 23)
 * - Import external papers to library
 * - Real-time search results
 */

import { Search as SearchIcon, Globe, Plus, RefreshCw, BarChart2, Hash, ExternalLink, Calendar, Users, TrendingUp, Layers } from "lucide-react";
import { clsx } from "clsx";
import { useState } from "react";
import { motion } from "motion/react";
import { useLanguage } from "../contexts/LanguageContext";
import { useSearch } from "@/hooks/useSearch";
import { useAutocomplete } from "@/hooks/useAutocomplete";
import { SearchResultCard } from "../components/SearchResultCard";
import { AuthorResultCard } from "../components/AuthorResultCard";
import { AutocompleteDropdown } from "../components/AutocompleteDropdown";
import { SearchFilters } from "../components/SearchFilters";
import * as papersApi from "@/services/papersApi";
import * as searchApi from "@/services/searchApi";
import { AuthorSearchResult } from "@/services/searchApi";
import toast from "react-hot-toast";
import { NoSearchResultsState } from "../components/EmptyState";

export function Search() {
  const [activeSource, setActiveSource] = useState("all");
  const { language } = useLanguage();
  const isZh = language === "zh";

  // Search filters state
  const [searchFilters, setSearchFilters] = useState<{
    sources?: string[];
    yearFrom?: number;
    yearTo?: number;
    author?: string;
    sortBy?: 'relevance' | 'date';
  }>({});

  // Main search hook
  const {
    query,
    setQuery,
    results,
    loading,
    error,
  } = useSearch(300); // D-11: 300ms debounce

  // Autocomplete hook (Phase 23)
  const {
    results: autocompleteResults,
    loading: autocompleteLoading,
    clear: clearAutocomplete,
  } = useAutocomplete({ minChars: 3, debounceMs: 300, limit: 5 });

  // Author search state (Phase 23)
  const [authorResults, setAuthorResults] = useState<AuthorSearchResult[]>([]);
  const [authorLoading, setAuthorLoading] = useState(false);

  const t = {
    sources: isZh ? "检索来源" : "Sources",
    global: isZh ? "全局搜索" : "Global",
    aggregators: isZh ? "聚合引擎" : "Aggregators",
    allSources: isZh ? "全部来源" : "All Sources",
    connectors: isZh ? "连接器" : "Connectors",
    statusConn: isZh ? "已连接" : "Connected",
    statusLimit: isZh ? "频率限制" : "Rate Limited",
    statusDisconn: isZh ? "未连接" : "Disconnected",
    refresh: isZh ? "刷新令牌" : "Refresh Tokens",
    query: isZh ? "查询" : "Query",
    placeholder: isZh ? "输入检索词，例如自主智能体、大模型..." : "Search for autonomous agents, LLMs...",
    loadMore: isZh ? "加载更多结果" : "Load More Results",
    import: isZh ? "导入" : "Import",
    analyze: isZh ? "分析" : "Analyze",
    source: isZh ? "原文" : "Source",
    analysis: isZh ? "检索分析" : "Analysis",
    velocity: isZh ? "发表趋势" : "Velocity",
    topAuthors: isZh ? "热门作者" : "Top Authors",
    topics: isZh ? "提取主题" : "Topics",
    report: isZh ? "生成报告" : "Report",
    tagNames: isZh ? ["大语言模型", "智能体", "推理", "思维链", "工具调用", "模拟"] : ["LLMs", "Agentic", "Reasoning", "Chain-of-Thought", "Tool Use", "Simulation"],
    yourLibrary: isZh ? "您的论文库" : "Your Library",
    externalSources: isZh ? "外部来源" : "External Sources",
    searching: isZh ? "搜索中..." : "Searching...",
    noResults: isZh ? "未找到结果" : "No results found",
    startTyping: isZh ? "输入关键词开始搜索" : "Start typing to search",
    importSuccess: isZh ? "论文已添加到您的库中" : "Paper added to your library",
    importError: isZh ? "导入失败" : "Import failed",
    authors: isZh ? "作者" : "Authors",
    authorResults: isZh ? "作者搜索结果" : "Author Results",
  };

  // Author search handler (Phase 23)
  const handleAuthorSearch = async (searchQuery: string) => {
    if (searchQuery.length < 3) return;
    setAuthorLoading(true);
    try {
      const response = await searchApi.searchAuthors(searchQuery);
      setAuthorResults(response.data);
    } catch (error) {
      console.error('Author search failed:', error);
    } finally {
      setAuthorLoading(false);
    }
  };

  // Trigger author search when query changes and author tab is active
  const handleSourceChange = (sourceId: string) => {
    setActiveSource(sourceId);
    if (sourceId === "authors" && query.length >= 3) {
      handleAuthorSearch(query);
    }
  };

  const SOURCES = [
    { id: "arxiv", name: "arXiv.org", status: t.statusConn, statusType: "Connected", results: results?.external.filter(r => r.source === 'arxiv').length || 0 },
    { id: "s2", name: "Semantic Scholar", status: t.statusConn, statusType: "Connected", results: results?.external.filter(r => r.source === 's2').length || 0 },
    { id: "authors", name: t.authors, status: t.statusConn, statusType: "Connected", results: authorResults.length },
  ];

  const handleAddToLibrary = async (result: any) => {
    try {
      await papersApi.createFromExternal({
        source: result.source,
        externalId: result.externalId || result.id,
        title: result.title,
        authors: result.authors,
        year: result.year,
        abstract: result.abstract,
        pdfUrl: result.pdfUrl,
      });
      toast.success(t.importSuccess);
    } catch (error: any) {
      console.error('Failed to import paper:', error);
      toast.error(error.response?.data?.error?.detail || t.importError);
    }
  };

  const handleViewPaper = (paperId: string) => {
    // Navigate to paper details (will be implemented in future)
    console.log('View paper:', paperId);
  };

  const getTotalResults = () => {
    if (!results) return 0;
    return results.internal.length + results.external.length;
  };

  return (
    <div className="h-full flex font-sans bg-background text-foreground relative selection:bg-primary selection:text-primary-foreground">
      {/* Column 1: Sources (Left) */}
      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5 }}
        className="w-[220px] border-r border-border/50 flex flex-col h-full bg-muted/20 flex-shrink-0"
      >
        <div className="px-5 py-4 border-b border-border/50 bg-background/80 backdrop-blur-md sticky top-0 z-10 flex justify-between items-center">
          <h2 className="font-serif text-xl font-black tracking-tight leading-none mb-1">{t.sources}</h2>
          <p className="text-[8px] font-bold tracking-[0.2em] uppercase text-primary">{t.global}</p>
        </div>

        <div className="flex-1 overflow-y-auto py-5 flex flex-col gap-6 px-4">
          <div>
            <div className="text-[9px] font-bold tracking-[0.2em] uppercase text-muted-foreground mb-3 px-1 border-b border-border/50 pb-1.5">{t.aggregators}</div>
            <button
              onClick={() => setActiveSource("all")}
              className={clsx(
                "flex items-center gap-2.5 px-2 py-2 rounded-sm transition-colors group w-full",
                activeSource === "all" ? "bg-primary text-primary-foreground shadow-sm shadow-primary/20" : "hover:bg-muted text-foreground/80 hover:text-primary"
              )}
            >
              <Globe className={clsx("w-3.5 h-3.5", activeSource === "all" ? "text-primary-foreground" : "text-primary")} />
              <span className="text-[10px] font-bold uppercase tracking-widest flex-1 text-left">{t.allSources}</span>
              <span className={clsx("text-[9px] font-mono", activeSource === "all" ? "text-primary-foreground/70" : "text-muted-foreground")}>{getTotalResults()}</span>
            </button>
          </div>

          <div>
            <div className="text-[9px] font-bold tracking-[0.2em] uppercase text-muted-foreground mb-3 px-1 border-b border-border/50 pb-1.5">{t.connectors}</div>
            <div className="flex flex-col gap-0.5">
              {SOURCES.map((source) => (
                <button
                  key={source.id}
                  onClick={() => handleSourceChange(source.id)}
                  className={clsx(
                    "flex items-center gap-2.5 px-2 py-2 rounded-sm transition-colors group w-full",
                    activeSource === source.id ? "bg-primary text-primary-foreground shadow-sm shadow-primary/20" : "hover:bg-muted text-foreground/80 hover:text-primary"
                  )}
                >
                  <div className={clsx(
                    "w-1.5 h-1.5 rounded-full flex-shrink-0",
                    source.statusType === "Connected" ? "bg-green-500" : source.statusType === "Rate Limited" ? "bg-yellow-500" : "bg-red-500"
                  )} />
                  <span className="text-[10px] font-bold uppercase tracking-widest flex-1 text-left truncate">{source.name}</span>
                  {source.results > 0 && <span className={clsx("text-[9px] font-mono", activeSource === source.id ? "text-primary-foreground/70" : "text-muted-foreground")}>{source.results}</span>}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="p-4 border-t border-border/50 bg-background/80 backdrop-blur-md">
          <button className="w-full border border-foreground/20 text-foreground py-2.5 rounded-sm text-[9px] font-bold uppercase tracking-[0.2em] hover:bg-muted transition-colors flex items-center justify-center gap-2 group shadow-sm bg-card">
            <RefreshCw className="w-3 h-3 group-hover:rotate-180 transition-transform duration-500" />
            {t.refresh}
          </button>
        </div>
      </motion.div>

      {/* Column 2: Search Interface & Results (Middle) */}
      <div className="flex-1 flex flex-col h-full bg-background min-w-[500px]">
        <div className="px-5 py-4 border-b border-border/50 bg-background/90 backdrop-blur-md sticky top-0 z-10 flex flex-col gap-3 shadow-sm">
          <div className="flex justify-between items-center gap-4">
            <div className="relative flex-1 max-w-2xl">
              <div className="flex items-center gap-3 bg-card border border-primary/30 p-1 rounded-full focus-within:border-primary transition-colors shadow-sm group">
                <SearchIcon className="w-4 h-4 text-primary ml-3" />
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className="flex-1 bg-transparent border-none text-sm font-serif font-bold tracking-wide focus:outline-none focus:ring-0 placeholder:font-sans placeholder:font-normal placeholder:tracking-normal placeholder:text-muted-foreground"
                  placeholder={t.placeholder}
                />
                <button className="bg-primary text-primary-foreground px-4 py-1.5 rounded-full text-[10px] font-bold uppercase tracking-[0.2em] hover:bg-secondary transition-colors h-full shadow-sm shadow-primary/20">
                  {t.query}
                </button>
              </div>
              {/* Autocomplete Dropdown (Phase 23) */}
              <AutocompleteDropdown
                results={autocompleteResults}
                loading={autocompleteLoading}
                visible={query.length >= 3 && activeSource !== "authors"}
                onSelect={(paper) => {
                  console.log('Selected paper:', paper);
                  clearAutocomplete();
                }}
              />
            </div>
            {results && (
              <div className="text-[9px] font-mono tracking-[0.2em] text-muted-foreground flex-shrink-0">
                {getTotalResults()} {isZh ? "条结果" : "results"}
              </div>
            )}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto bg-muted/5 p-5">
          {loading && (
            <div className="flex items-center justify-center h-64">
              <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
                {t.searching}
              </div>
            </div>
          )}

          {error && (
            <div className="flex items-center justify-center h-64">
              <div className="text-sm text-red-500">{error}</div>
            </div>
          )}

          {!loading && !error && !results && (
            <div className="flex items-center justify-center h-64">
              <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
                {t.startTyping}
              </div>
            </div>
          )}

          {results && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="space-y-8"
            >
              {/* Author Results (Phase 23) */}
              {activeSource === "authors" && (
                <div>
                  <h2 className="font-semibold mb-4 text-lg">{t.authorResults} ({authorResults.length})</h2>
                  {authorLoading ? (
                    <div className="flex items-center justify-center h-32">
                      <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
                        {t.searching}
                      </div>
                    </div>
                  ) : authorResults.length > 0 ? (
                    <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
                      {authorResults.map((author) => (
                        <AuthorResultCard
                          key={author.authorId}
                          author={author}
                          onClick={(a) => console.log('Selected author:', a)}
                        />
                      ))}
                    </div>
                  ) : (
                    <NoSearchResultsState query={query} />
                  )}
                </div>
              )}

              {/* Internal Results */}
              {activeSource !== "authors" && results.internal.length > 0 && (
                <div>
                  <h2 className="font-semibold mb-4 text-lg">{t.yourLibrary} ({results.internal.length})</h2>
                  <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
                    {results.internal.map((r) => (
                      <SearchResultCard
                        key={r.id}
                        result={{ ...r, source: 'internal' }}
                        onViewPaper={handleViewPaper}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* External Results */}
              {activeSource !== "authors" && results.external.length > 0 && (
                <div>
                  <h2 className="font-semibold mb-4 text-lg">{t.externalSources} ({results.external.length})</h2>
                  <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
                    {results.external.map((r, i) => (
                      <SearchResultCard
                        key={i}
                        result={r}
                        onAddToLibrary={handleAddToLibrary}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* No Results */}
              {activeSource !== "authors" && results.internal.length === 0 && results.external.length === 0 && (
                <NoSearchResultsState query={query} />
              )}
            </motion.div>
          )}
        </div>
      </div>

      {/* Column 3: Analysis & Filters (Right) */}
      <motion.div
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5 }}
        className="w-[240px] border-l border-border/50 flex flex-col h-full bg-muted/10 flex-shrink-0 relative"
      >
        <div className="px-5 py-4 border-b border-border/50 bg-background/80 backdrop-blur-md sticky top-0 z-10 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BarChart2 className="w-3.5 h-3.5 text-primary" />
            <h2 className="font-serif text-lg font-bold tracking-tight">{t.analysis}</h2>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-6 flex flex-col gap-8">

          {/* Search Filters Component */}
          <SearchFilters filters={searchFilters} onFilterChange={setSearchFilters} />

          {/* Publication Year Histogram */}
          <div className="flex flex-col gap-3">
            <h3 className="text-[9px] font-bold tracking-[0.3em] uppercase text-muted-foreground border-b border-border/50 pb-1.5 flex items-center gap-1.5">
              <Calendar className="w-3 h-3" /> {t.velocity}
            </h3>
            <div className="flex items-end gap-1 h-20 mt-2">
              <div className="w-full bg-muted/50 rounded-sm hover:bg-primary/80 transition-colors h-[20%] relative group"></div>
              <div className="w-full bg-muted/50 rounded-sm hover:bg-primary/80 transition-colors h-[30%] relative group"></div>
              <div className="w-full bg-muted/50 rounded-sm hover:bg-primary/80 transition-colors h-[50%] relative group"></div>
              <div className="w-full bg-primary rounded-sm transition-colors h-[90%] relative group shadow-sm shadow-primary/20">
                <span className="absolute -top-5 left-1/2 -translate-x-1/2 text-[8px] font-mono text-primary font-bold">{results?.external.length || 0}</span>
              </div>
              <div className="w-full bg-muted/50 rounded-sm hover:bg-primary/80 transition-colors h-[60%] relative group"></div>
            </div>
            <div className="flex justify-between text-[8px] font-mono text-muted-foreground mt-1">
              <span>2019</span>
              <span className="text-primary font-bold">2022</span>
              <span>2024</span>
            </div>
          </div>

          {/* Top Authors */}
          <div className="flex flex-col gap-3">
            <h3 className="text-[9px] font-bold tracking-[0.3em] uppercase text-muted-foreground border-b border-border/50 pb-1.5 flex items-center gap-1.5">
              <Users className="w-3 h-3" /> {t.topAuthors}
            </h3>
            <div className="flex flex-col gap-2 mt-1">
              {results?.external.slice(0, 4).flatMap(r => r.authors || []).slice(0, 4).map((author, i) => (
                <div key={i} className="flex flex-col gap-1 group cursor-pointer">
                  <div className="flex justify-between items-center">
                    <span className="text-xs font-medium text-foreground/80 group-hover:text-primary transition-colors">{author}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Extracted Topics */}
          <div className="flex flex-col gap-3">
            <h3 className="text-[9px] font-bold tracking-[0.3em] uppercase text-muted-foreground border-b border-border/50 pb-1.5 flex items-center gap-1.5">
              <Hash className="w-3 h-3" /> {t.topics}
            </h3>
            <div className="flex flex-wrap gap-1.5 mt-1">
              {t.tagNames.map((tag) => (
                <span key={tag} className="font-sans text-[9px] font-bold uppercase tracking-[0.1em] bg-card border border-border/50 text-foreground/70 px-2 py-1 rounded-sm hover:bg-primary hover:text-primary-foreground hover:border-primary transition-colors cursor-pointer shadow-sm">
                  {tag}
                </span>
              ))}
            </div>
          </div>

        </div>

        <div className="px-5 py-4 border-t border-border/50 bg-background/80 backdrop-blur-md">
          <button className="w-full bg-transparent border border-foreground/20 text-foreground py-2 rounded-sm text-[9px] font-bold uppercase tracking-[0.2em] hover:bg-muted transition-colors flex justify-center items-center gap-2">
            <TrendingUp className="w-3.5 h-3.5 text-foreground/50" />
            {t.report}
          </button>
        </div>
      </motion.div>
    </div>
  );
}