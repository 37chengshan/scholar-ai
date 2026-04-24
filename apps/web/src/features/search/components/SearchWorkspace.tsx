import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router';
import { BarChart2, Calendar, Database, Users } from 'lucide-react';
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
  const [showInspector, setShowInspector] = useState(true);

  const workspace = useSearchWorkspace();
  const {
    query,
    setQuery,
    submitSearch,
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
    currentQuery: isZh ? '当前检索' : 'Current Query',
    resultMix: isZh ? '结果分布' : 'Result Mix',
    yearCoverage: isZh ? '年份分布' : 'Year Coverage',
    topAuthors: isZh ? '热门作者' : 'Top Authors',
    waitingForQuery: isZh ? '等待输入关键词' : 'Waiting for a search term',
    noSummaryData: isZh ? '当前页暂无可展示的检索摘要' : 'No summary is available for this page yet',
    noYearData: isZh ? '当前结果缺少年份信息' : 'Year data is not available for these results',
    noAuthorData: isZh ? '当前结果缺少作者信息' : 'Author data is not available for these results',
    library: isZh ? '库内' : 'Library',
    resultUnit: isZh ? '条' : 'items',
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
    authorMinChars: isZh ? '输入至少 3 个字符搜索作者' : 'Enter at least 3 characters to search authors',
    externalDegraded: isZh ? '部分外部来源暂时失败，已展示可用结果。' : 'Some external sources are degraded; showing available results.',
    emptyLibrary: isZh ? '本地库无结果，可尝试外部来源。' : 'No local results. Try external sources.',
    emptyExternal: isZh ? '外部来源无结果或暂不可用。' : 'No external results or source unavailable.',
    emptyAll: isZh ? '没有找到相关论文，试试更短关键词。' : 'No papers found. Try a shorter query.',
    process: isZh ? '检索过程' : 'Retrieval Process',
    queryType: isZh ? '查询类型' : 'Query type',
    rewriteCount: isZh ? '检索改写数' : 'Rewrite count',
    rewrittenQuery: isZh ? '改写后查询' : 'Rewritten query',
    secondPass: isZh ? '是否二次检索' : 'Second pass',
    secondPassGain: isZh ? '二次检索收益' : 'Second-pass gain',
    evidenceHits: isZh ? '命中证据数' : 'Evidence hits',
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

  const plannerMetaRows = useMemo(() => {
    const metadata = results?.metadata;
    if (!metadata) {
      return [];
    }
    return [
      { label: labels.queryType, value: metadata.query_family },
      { label: labels.rewriteCount, value: metadata.planner_query_count },
      { label: labels.rewrittenQuery, value: metadata.decontextualized_query },
      { label: labels.secondPass, value: metadata.second_pass_used !== undefined ? (metadata.second_pass_used ? (isZh ? '是' : 'Yes') : (isZh ? '否' : 'No')) : undefined },
      { label: labels.secondPassGain, value: metadata.second_pass_gain },
      { label: labels.evidenceHits, value: metadata.evidence_bundle_hit_count },
    ].filter((row) => row.value !== undefined && row.value !== null && row.value !== '');
  }, [isZh, labels.evidenceHits, labels.queryType, labels.rewriteCount, labels.rewrittenQuery, labels.secondPass, labels.secondPassGain, results?.metadata]);

  const statusLine = useMemo(() => {
    const sourceLabel = workspace.activeSource === 'authors'
      ? (isZh ? '作者来源' : 'Author source')
      : workspace.activeSource === 'arxiv'
        ? 'arXiv'
        : workspace.activeSource === 's2'
          ? 'Semantic Scholar'
          : (isZh ? 'arXiv + Semantic Scholar + 本地库' : 'arXiv + Semantic Scholar + Library');
    if (isInitialLoading) {
      return isZh ? `正在搜索 ${sourceLabel} · 第 1 页` : `Searching ${sourceLabel} · page 1`;
    }
    if (isPageFetching) {
      return isZh ? `正在获取第 ${page + 1} 页...` : `Fetching page ${page + 1}...`;
    }
    if (error && results) {
      return labels.externalDegraded;
    }
    return isZh
      ? `来源：${sourceLabel} · 排序：${workspace.sortBy === 'date' ? '时间' : '相关度'}`
      : `Source: ${sourceLabel} · Sort: ${workspace.sortBy === 'date' ? 'Date' : 'Relevance'}`;
  }, [error, isInitialLoading, isPageFetching, isZh, labels.externalDegraded, page, results, workspace.activeSource, workspace.sortBy]);

  const visibleResults = useMemo(
    () => (results ? [...results.internal, ...results.external] : []),
    [results],
  );

  const sourceSummaryRows = useMemo(() => {
    if (!results) {
      return [];
    }

    return [
      { label: labels.library, count: results.internal.length },
      { label: 'arXiv', count: results.external.filter((result) => result.source === 'arxiv').length },
      { label: 'Semantic Scholar', count: results.external.filter((result) => result.source === 's2').length },
    ].filter((row) => row.count > 0);
  }, [labels.library, results]);

  const yearSummaryRows = useMemo(() => {
    const yearCounts = new Map<number, number>();

    visibleResults.forEach((result) => {
      if (result.year) {
        yearCounts.set(result.year, (yearCounts.get(result.year) ?? 0) + 1);
      }
    });

    return Array.from(yearCounts.entries())
      .sort((left, right) => right[1] - left[1] || right[0] - left[0])
      .slice(0, 4)
      .map(([year, count]) => ({ label: String(year), count }));
  }, [visibleResults]);

  const authorSummaryRows = useMemo(() => {
    const authorCounts = new Map<string, number>();

    visibleResults.forEach((result) => {
      result.authors?.forEach((author) => {
        const normalizedAuthor = author.trim();
        if (!normalizedAuthor) {
          return;
        }
        authorCounts.set(normalizedAuthor, (authorCounts.get(normalizedAuthor) ?? 0) + 1);
      });
    });

    return Array.from(authorCounts.entries())
      .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]))
      .slice(0, 5)
      .map(([label, count]) => ({ label, count }));
  }, [visibleResults]);

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
          onSubmitSearch={submitSearch}
          placeholder={labels.placeholder}
          queryLabel={labels.query}
          total={results?.total}
          isZh={isZh}
          inspectorOpen={showInspector}
          onToggleInspector={() => setShowInspector((value) => !value)}
          statusLine={statusLine}
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
              authorMinChars: labels.authorMinChars,
              externalDegraded: labels.externalDegraded,
              emptyLibrary: labels.emptyLibrary,
              emptyExternal: labels.emptyExternal,
              emptyAll: labels.emptyAll,
            }}
            onViewPaper={(paperId) => navigate(`/read/${paperId}?source=search`)}
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

      {showInspector ? (
      <motion.aside
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5 }}
        className="hidden h-full w-[280px] flex-shrink-0 border-l border-border/50 bg-muted/10 lg:flex flex-col"
      >
        <div className="px-5 py-4 border-b border-border/50 bg-background/80 backdrop-blur-md sticky top-0 z-10">
          <div className="flex items-center gap-2">
            <BarChart2 className="w-3.5 h-3.5 text-primary" />
            <h2 className="font-serif text-lg font-bold tracking-tight">{labels.analysis}</h2>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-6 flex flex-col gap-8">
          <section className="flex flex-col gap-3">
            <h3 className="text-[9px] font-bold tracking-[0.3em] uppercase text-muted-foreground border-b border-border/50 pb-1.5 flex items-center gap-1.5">
              {labels.currentQuery}
            </h3>
            <div className="mt-1 font-serif text-xl leading-tight text-foreground line-clamp-3">
              {query || labels.waitingForQuery}
            </div>
            <div className="mt-2 rounded-sm bg-muted/30 px-3 py-3 border border-border/50">
              <SearchFilters
                filters={{ sortBy: workspace.sortBy }}
                onFilterChange={(nextFilters) => {
                  if (nextFilters.sortBy) {
                    workspace.updateSortBy(nextFilters.sortBy);
                  }
                }}
              />
            </div>
          </section>

          <section className="flex flex-col gap-3">
            <h3 className="text-[9px] font-bold tracking-[0.3em] uppercase text-muted-foreground border-b border-border/50 pb-1.5 flex items-center gap-1.5">
              <Database className="w-3 h-3" /> {labels.resultMix}
            </h3>
            {sourceSummaryRows.length > 0 ? (
              <div className="mt-1 space-y-2">
                {sourceSummaryRows.map((row) => {
                  const share = Math.round((row.count / Math.max(visibleResults.length, 1)) * 100);
                  return (
                    <div key={row.label} className="grid grid-cols-[1fr_auto] items-center gap-3 text-[11px]">
                      <div className="min-w-0">
                        <div className="font-medium text-foreground truncate">{row.label}</div>
                        <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-muted/50">
                          <div
                            className="h-full rounded-full bg-primary/80"
                            style={{ width: `${Math.max(share, row.count > 0 ? 8 : 0)}%` }}
                          />
                        </div>
                      </div>
                      <div className="text-right font-mono text-muted-foreground">
                        <div>{row.count}</div>
                        <div className="text-[9px]">{share}%</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-[11px] text-muted-foreground">{labels.noSummaryData}</p>
            )}
          </section>

          <section className="flex flex-col gap-3">
            <h3 className="text-[9px] font-bold tracking-[0.3em] uppercase text-muted-foreground border-b border-border/50 pb-1.5 flex items-center gap-1.5">
              <Calendar className="w-3 h-3" /> {labels.yearCoverage}
            </h3>
            {yearSummaryRows.length > 0 ? (
              <div className="mt-1 space-y-2">
                {yearSummaryRows.map((row) => (
                  <div key={row.label} className="flex items-center justify-between gap-3 text-[11px]">
                    <span className="font-medium text-foreground">{row.label}</span>
                    <span className="font-mono text-muted-foreground">
                      {row.count} {labels.resultUnit}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-[11px] text-muted-foreground">{labels.noYearData}</p>
            )}
          </section>

          <section className="flex flex-col gap-3">
            <h3 className="text-[9px] font-bold tracking-[0.3em] uppercase text-muted-foreground border-b border-border/50 pb-1.5 flex items-center gap-1.5">
              <Users className="w-3 h-3" /> {labels.topAuthors}
            </h3>
            {authorSummaryRows.length > 0 ? (
              <div className="mt-1 space-y-2">
                {authorSummaryRows.map((row) => (
                  <div key={row.label} className="flex items-center justify-between gap-3 text-[11px]">
                    <span className="truncate font-medium text-foreground">{row.label}</span>
                    <span className="font-mono text-muted-foreground">
                      {row.count} {labels.resultUnit}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-[11px] text-muted-foreground">{labels.noAuthorData}</p>
            )}
          </section>

          <details className="flex flex-col gap-3" open={false}>
            <summary className="cursor-pointer text-[9px] font-bold tracking-[0.3em] uppercase text-muted-foreground border-b border-border/50 pb-1.5">
              {labels.process}
            </summary>
            {plannerMetaRows.length > 0 ? (
              <dl className="mt-1 space-y-2 text-[11px]">
                {plannerMetaRows.map((row) => (
                  <div key={row.label} className="grid grid-cols-[1fr_auto] items-start gap-2">
                    <dt className="text-muted-foreground">{row.label}</dt>
                    <dd className="text-foreground break-all text-right">{String(row.value)}</dd>
                  </div>
                ))}
              </dl>
            ) : (
              <p className="text-[11px] text-muted-foreground">
                {isZh ? '当前结果暂无检索过程元数据' : 'Retrieval process metadata is not available for this result set'}
              </p>
            )}
          </details>
        </div>

      </motion.aside>
      ) : null}

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
