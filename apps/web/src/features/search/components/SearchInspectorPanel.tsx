import { BarChart2, Calendar, Database, Users } from 'lucide-react';
import { motion } from 'motion/react';

import { SearchFilters } from '@/app/components/SearchFilters';
import { Button } from '@/app/components/ui/button';
import type { LayeredEvidenceSearchResult } from '@/services/searchApi';

interface SearchInspectorLabels {
  analysis: string;
  currentQuery: string;
  waitingForQuery: string;
  resultMix: string;
  noSummaryData: string;
  yearCoverage: string;
  resultUnit: string;
  noYearData: string;
  topAuthors: string;
  noAuthorData: string;
  process: string;
}

interface SearchInspectorPanelProps {
  labels: SearchInspectorLabels;
  query: string;
  sortBy: 'relevance' | 'date';
  onSortByChange: (sortBy: 'relevance' | 'date') => void;
  sourceSummaryRows: Array<{ label: string; count: number }>;
  yearSummaryRows: Array<{ label: string; count: number }>;
  authorSummaryRows: Array<{ label: string; count: number }>;
  visibleResultCount: number;
  layeredEvidence: LayeredEvidenceSearchResult | null;
  plannerMetaRows: Array<{ label: string; value: unknown }>;
  isZh: boolean;
  onOpenEvidence: (item: LayeredEvidenceSearchResult['evidence_matches'][number]) => void;
  onSaveEvidence: (item: LayeredEvidenceSearchResult['evidence_matches'][number]) => void;
}

export function SearchInspectorPanel({
  labels,
  query,
  sortBy,
  onSortByChange,
  sourceSummaryRows,
  yearSummaryRows,
  authorSummaryRows,
  visibleResultCount,
  layeredEvidence,
  plannerMetaRows,
  isZh,
  onOpenEvidence,
  onSaveEvidence,
}: SearchInspectorPanelProps) {
  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.5 }}
      className="h-full flex flex-col bg-muted/10"
    >
      <div className="px-5 py-4 border-b border-border/50 bg-background/80 backdrop-blur-md sticky top-0 z-10">
        <div className="flex items-center gap-2">
          <BarChart2 className="w-3.5 h-3.5 text-primary" />
          <h2 className="font-serif text-lg font-bold tracking-tight">{labels.analysis}</h2>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-6 flex flex-col gap-8">
        <section className="flex flex-col gap-3">
          <h3 className="text-[9px] font-bold tracking-[0.3em] uppercase text-muted-foreground border-b border-border/50 pb-1.5 flex items-center gap-1.5 font-serif tracking-tight">
            {labels.currentQuery}
          </h3>
          <div className="mt-1 font-serif text-xl leading-tight text-foreground line-clamp-3">
            {query || labels.waitingForQuery}
          </div>
          <div className="mt-2 rounded-sm bg-muted/30 px-3 py-3 border border-border/50">
            <SearchFilters
              filters={{ sortBy }}
              onFilterChange={(nextFilters) => {
                if (nextFilters.sortBy) {
                  onSortByChange(nextFilters.sortBy);
                }
              }}
            />
          </div>
        </section>

        <section className="flex flex-col gap-3">
          <h3 className="text-[9px] font-bold tracking-[0.3em] uppercase text-muted-foreground border-b border-border/50 pb-1.5 flex items-center gap-1.5 font-serif tracking-tight">
            <Database className="w-3 h-3" /> {labels.resultMix}
          </h3>
          {sourceSummaryRows.length > 0 ? (
            <div className="mt-1 space-y-2">
              {sourceSummaryRows.map((row) => {
                const share = Math.round((row.count / Math.max(visibleResultCount, 1)) * 100);
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

        {layeredEvidence ? (
          <section className="flex flex-col gap-3">
            <h3 className="text-[9px] font-bold tracking-[0.3em] uppercase text-muted-foreground border-b border-border/50 pb-1.5 font-serif tracking-tight">
              {isZh ? '证据分层结果' : 'Layered Evidence'}
            </h3>
            <div className="grid grid-cols-2 gap-2 text-[11px]">
              <div className="rounded-md border border-border/60 bg-muted/20 px-2 py-1">paper {layeredEvidence.paper_results.length}</div>
              <div className="rounded-md border border-border/60 bg-muted/20 px-2 py-1">section {layeredEvidence.section_matches.length}</div>
              <div className="rounded-md border border-border/60 bg-muted/20 px-2 py-1">evidence {layeredEvidence.evidence_matches.length}</div>
              <div className="rounded-md border border-border/60 bg-muted/20 px-2 py-1">relation {layeredEvidence.relation_matches.length}</div>
            </div>

            <div className="space-y-2">
              {layeredEvidence.evidence_matches.slice(0, 3).map((item) => (
                <div
                  key={`${item.paper_id}-${item.source_chunk_id}`}
                  className="rounded-md border border-border/60 bg-background px-2 py-2 text-[11px]"
                >
                  <button
                    type="button"
                    className="w-full text-left hover:text-primary"
                    onClick={() => onOpenEvidence(item)}
                  >
                    <div className="font-medium text-foreground">{item.paper_id} · {item.section_path || 'section'}</div>
                    <div className="mt-1 line-clamp-2 text-muted-foreground">{item.content || item.source_chunk_id}</div>
                  </button>
                  <div className="mt-2 flex justify-end">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="h-7 text-[10px]"
                      onClick={() => onSaveEvidence(item)}
                    >
                      {isZh ? '保存到笔记' : 'Save to notes'}
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </section>
        ) : null}

        <section className="flex flex-col gap-3">
          <h3 className="text-[9px] font-bold tracking-[0.3em] uppercase text-muted-foreground border-b border-border/50 pb-1.5 flex items-center gap-1.5 font-serif tracking-tight">
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
          <h3 className="text-[9px] font-bold tracking-[0.3em] uppercase text-muted-foreground border-b border-border/50 pb-1.5 flex items-center gap-1.5 font-serif tracking-tight">
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
    </motion.div>
  );
}
