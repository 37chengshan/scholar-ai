import { useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router';
import { BarChart2, Calendar, Hash, TrendingUp, Users } from 'lucide-react';
import { motion } from 'motion/react';
import { useLanguage } from '@/app/contexts/LanguageContext';
import { SearchFilters } from '@/app/components/SearchFilters';
import { useSearchWorkspace } from '@/features/search/hooks/useSearchWorkspace';
import { useUnifiedSearch } from '@/features/search/hooks/useUnifiedSearch';
import { useAuthorSearch } from '@/features/search/hooks/useAuthorSearch';
import { useSearchImportFlow } from '@/features/search/hooks/useSearchImportFlow';
import { SearchSidebar } from '@/features/search/components/SearchSidebar';
import { SearchToolbar } from '@/features/search/components/SearchToolbar';
import { SearchPagination } from '@/features/search/components/SearchPagination';
import { SearchResultsPanel } from '@/features/search/components/SearchResultsPanel';
import { SearchAuthorPanel } from '@/features/search/components/SearchAuthorPanel';
import { SearchKnowledgeBaseImportModal } from '@/features/search/components/SearchKnowledgeBaseImportModal';

export function SearchWorkspace() {
  const { language } = useLanguage();
  const isZh = language === 'zh';
  const navigate = useNavigate();

  const workspace = useSearchWorkspace();
  const {
    query,
    setQuery,
    results,
    loading,
    isInitialLoading,
    isPageFetching,
    error,
    page,
    totalPages,
    nextPage,
    prevPage,
    hasMore,
    hasPrev,
    pageSize,
  } = useUnifiedSearch({
    sortBy: workspace.sortBy,
    initialQuery: workspace.queryFromUrl,
    initialPage: workspace.pageFromUrl,
  });

  const authorSearch = useAuthorSearch();
  const importFlow = useSearchImportFlow();

  const labels = {
    sources: isZh ? '检索来源' : 'Sources',
    global: isZh ? '全局搜索' : 'Global',
    aggregators: isZh ? '聚合引擎' : 'Aggregators',
    allSources: isZh ? '全部来源' : 'All Sources',
    connectors: isZh ? '连接器' : 'Connectors',
    query: isZh ? '查询' : 'Query',
    placeholder: isZh ? '输入检索词，例如自主智能体、大模型...' : 'Search for autonomous agents, LLMs...',
    prevPage: isZh ? '上一页' : 'Prev',
    nextPage: isZh ? '下一页' : 'Next',
    page: isZh ? '页' : 'Page',
    of: '/',
    importLabel: isZh ? '导入' : 'Import',
    analysis: isZh ? '检索分析' : 'Analysis',
    velocity: isZh ? '发表趋势' : 'Velocity',
    topAuthors: isZh ? '热门作者' : 'Top Authors',
    topics: isZh ? '提取主题' : 'Topics',
    report: isZh ? '生成报告' : 'Report',
    tagNames: isZh
      ? ['大语言模型', '智能体', '推理', '思维链', '工具调用', '模拟']
      : ['LLMs', 'Agentic', 'Reasoning', 'Chain-of-Thought', 'Tool Use', 'Simulation'],
    yourLibrary: isZh ? '您的论文库' : 'Your Library',
    externalSources: isZh ? '外部来源' : 'External Sources',
    searching: isZh ? '搜索中...' : 'Searching...',
    startTyping: isZh ? '输入关键词开始搜索' : 'Start typing to search',
    authorResults: isZh ? '作者搜索结果' : 'Author Results',
    noPapers: isZh ? '未找到论文' : 'No papers found',
    citations: isZh ? '引用' : 'Citations',
    kbImportTitle: isZh ? '选择知识库导入' : 'Choose Knowledge Base',
    loading: isZh ? '加载中...' : 'Loading...',
    noKB: isZh ? '暂无知识库，请先创建知识库' : 'No knowledge bases available',
    paperUnit: isZh ? '篇论文' : 'papers',
  };

  useEffect(() => {
    if (workspace.activeSource === 'authors' && query.length >= 3) {
      void authorSearch.searchAuthors(query);
      return;
    }
    if (workspace.activeSource === 'authors' && query.length < 3) {
      authorSearch.searchAuthors('');
    }
  }, [authorSearch.searchAuthors, query, workspace.activeSource]);

  const sources = useMemo(() => [
    {
      id: 'arxiv',
      name: 'arXiv.org',
      statusType: 'Connected' as const,
      results: results?.external.filter((result) => result.source === 'arxiv').length || 0,
    },
    {
      id: 's2',
      name: 'Semantic Scholar',
      statusType: 'Connected' as const,
      results: results?.external.filter((result) => result.source === 's2').length || 0,
    },
    {
      id: 'authors',
      name: isZh ? '作者' : 'Authors',
      statusType: 'Connected' as const,
      results: authorSearch.authorResults.length,
    },
  ], [authorSearch.authorResults.length, isZh, results]);

  const handleOpenAuthor = async (author: Parameters<typeof authorSearch.openAuthorPapers>[0]) => {
    workspace.setSelectedAuthorId(author.authorId);
    await authorSearch.openAuthorPapers(author);
  };

  const handleAddToLibrary = async (paper: any) => {
    await importFlow.startImportSelection(paper);
  };

  return (
    <section className="h-full flex font-sans bg-background text-foreground relative selection:bg-primary selection:text-primary-foreground" data-testid="search-workspace-root">
      <SearchSidebar
        activeSource={workspace.activeSource}
        setActiveSource={workspace.updateActiveSource}
        sources={sources}
        allResults={results?.total || 0}
        labels={{
          sources: labels.sources,
          global: labels.global,
          aggregators: labels.aggregators,
          allSources: labels.allSources,
          connectors: labels.connectors,
        }}
      />

      <div className="flex-1 flex flex-col h-full bg-paper-1 min-w-0 md:min-w-[500px]">
        <SearchToolbar
          query={query}
          onQueryChange={setQuery}
          placeholder={labels.placeholder}
          queryLabel={labels.query}
          total={results?.total}
          isZh={isZh}
        />

        <div className="flex-1 overflow-y-auto bg-paper-2/35 p-5">
          <SearchResultsPanel
            activeSource={workspace.activeSource}
            query={query}
            loading={loading}
            isInitialLoading={isInitialLoading}
            isPageFetching={isPageFetching}
            error={error}
            results={results}
            authorResults={authorSearch.authorResults}
            authorLoading={authorSearch.authorLoading}
            labels={{
              searching: labels.searching,
              startTyping: labels.startTyping,
              authorResults: labels.authorResults,
              yourLibrary: labels.yourLibrary,
              externalSources: labels.externalSources,
            }}
            onViewPaper={(paperId) => navigate(`/read/${paperId}`)}
            onAddToLibrary={handleAddToLibrary}
            onAuthorClick={handleOpenAuthor}
          />

          {workspace.activeSource !== 'authors' && !!results && results.total > pageSize && (
            <SearchPagination
              hasPrev={Boolean(hasPrev)}
              hasMore={Boolean(hasMore)}
              loading={isPageFetching}
              page={page}
              totalPages={totalPages}
              prevPage={prevPage}
              nextPage={nextPage}
              labels={{
                prevPage: labels.prevPage,
                nextPage: labels.nextPage,
                page: labels.page,
                of: labels.of,
              }}
            />
          )}
        </div>
      </div>

      <motion.aside
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5 }}
        className="w-[240px] border-l border-border/70 flex flex-col h-full bg-paper-2 flex-shrink-0 relative"
      >
        <div className="px-5 py-4 border-b border-border/60 bg-paper-1/80 backdrop-blur-md sticky top-0 z-10 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BarChart2 className="w-3.5 h-3.5 text-primary" />
            <h2 className="font-serif text-lg font-semibold tracking-tight">{labels.analysis}</h2>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-6 flex flex-col gap-8">
          <SearchFilters
            filters={{ sortBy: workspace.sortBy }}
            onFilterChange={(nextFilters) => {
              if (nextFilters.sortBy) {
                workspace.updateSortBy(nextFilters.sortBy);
              }
            }}
          />

          <div className="flex flex-col gap-3">
            <h3 className="editorial-rule-heading flex items-center gap-1.5">
              <Calendar className="w-3 h-3" /> {labels.velocity}
            </h3>
            <div className="flex items-end gap-1 h-20 mt-2">
              <div className="w-full bg-muted/50 rounded-sm h-[20%]" />
              <div className="w-full bg-muted/50 rounded-sm h-[30%]" />
              <div className="w-full bg-muted/50 rounded-sm h-[50%]" />
              <div className="w-full bg-primary rounded-sm h-[90%] shadow-sm shadow-primary/20">
                <span className="absolute text-[8px] font-mono text-primary font-bold">{results?.external.length || 0}</span>
              </div>
              <div className="w-full bg-muted/50 rounded-sm h-[60%]" />
            </div>
            <div className="flex justify-between text-[8px] font-mono text-muted-foreground mt-1">
              <span>2019</span>
              <span className="text-primary font-bold">2022</span>
              <span>2024</span>
            </div>
          </div>

          <div className="flex flex-col gap-3">
            <h3 className="editorial-rule-heading flex items-center gap-1.5">
              <Users className="w-3 h-3" /> {labels.topAuthors}
            </h3>
            <div className="flex flex-col gap-2 mt-1">
              {results?.external
                .slice(0, 4)
                .flatMap((result) => result.authors || [])
                .slice(0, 4)
                .map((author, index) => (
                  <div key={`${author}-${index}`} className="text-xs font-medium text-foreground/80">
                    {author}
                  </div>
                ))}
            </div>
          </div>

          <div className="flex flex-col gap-3">
            <h3 className="editorial-rule-heading flex items-center gap-1.5">
              <Hash className="w-3 h-3" /> {labels.topics}
            </h3>
            <div className="flex flex-wrap gap-1.5 mt-1">
              {labels.tagNames.map((tag) => (
                <span key={tag} className="font-sans text-[10px] font-semibold tracking-wide bg-paper-1 border border-border/60 text-foreground/75 px-2 py-1 rounded-sm">
                  {tag}
                </span>
              ))}
            </div>
          </div>
        </div>

        <div className="px-5 py-4 border-t border-border/60 bg-paper-1/80 backdrop-blur-md">
          <button className="w-full bg-transparent border border-foreground/20 text-foreground py-2 rounded-sm text-[10px] font-semibold tracking-wide hover:bg-muted transition-colors flex justify-center items-center gap-2">
            <TrendingUp className="w-3.5 h-3.5 text-foreground/50" />
            {labels.report}
          </button>
        </div>
      </motion.aside>

      <SearchAuthorPanel
        open={authorSearch.showAuthorPapersModal}
        selectedAuthor={authorSearch.selectedAuthor}
        authorPapers={authorSearch.authorPapers}
        loadingAuthorPapers={authorSearch.loadingAuthorPapers}
        labels={{
          searching: labels.searching,
          importLabel: labels.importLabel,
          emptyText: labels.noPapers,
          citations: labels.citations,
        }}
        onClose={() => authorSearch.setShowAuthorPapersModal(false)}
        onImportPaper={async (paper) => {
          await handleAddToLibrary(paper);
          authorSearch.setShowAuthorPapersModal(false);
        }}
      />

      <SearchKnowledgeBaseImportModal
        open={importFlow.showKBSelectModal}
        loadingKnowledgeBases={importFlow.loadingKBs}
        knowledgeBases={importFlow.knowledgeBases}
        importingPaperId={importFlow.importingPaperId}
        labels={{
          title: labels.kbImportTitle,
          loading: labels.loading,
          empty: labels.noKB,
          papersUnit: labels.paperUnit,
        }}
        onClose={() => {
          importFlow.cancelImport();
          importFlow.setShowKBSelectModal(false);
          importFlow.clearPendingImport();
        }}
        onConfirmImport={importFlow.importToKnowledgeBase}
      />
    </section>
  );
}
