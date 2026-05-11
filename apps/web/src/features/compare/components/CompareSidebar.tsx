import { BookOpen, Loader2, Plus, Search, X } from 'lucide-react';

import type { Paper } from '@/types';
import type { CompareDimensionId } from '@/services/compareApi';
import { ALLOWED_COMPARE_DIMENSIONS, DIMENSION_LABELS } from '@/services/compareApi';
import { Button } from '@/app/components/ui/button';
import { ScrollArea } from '@/app/components/ui/scroll-area';

function PaperChip({
  paper,
  onRemove,
}: {
  paper: Paper;
  onRemove: () => void;
}) {
  return (
    <div className="flex items-center gap-1 rounded-full border border-border/60 bg-background px-2 py-1 text-sm">
      <span className="max-w-[200px] truncate">{paper.title}</span>
      <button type="button" onClick={onRemove} className="ml-1 text-muted-foreground hover:text-foreground">
        <X className="h-3 w-3" />
      </button>
    </div>
  );
}

interface CompareSidebarProps {
  isZh: boolean;
  selectedPapers: Paper[];
  selectionNotice: string | null;
  searchQuery: string;
  searchLoading: boolean;
  searchResults: Paper[];
  enabledDims: Set<CompareDimensionId>;
  question: string;
  compareLoading: boolean;
  onSearchQueryChange: (value: string) => void;
  onSearch: () => void;
  onAddPaper: (paper: Paper) => void;
  onRemovePaper: (paperId: string) => void;
  onToggleDim: (dimId: CompareDimensionId) => void;
  onQuestionChange: (value: string) => void;
  onCompare: () => void;
}

export function CompareSidebar({
  isZh,
  selectedPapers,
  selectionNotice,
  searchQuery,
  searchLoading,
  searchResults,
  enabledDims,
  question,
  compareLoading,
  onSearchQueryChange,
  onSearch,
  onAddPaper,
  onRemovePaper,
  onToggleDim,
  onQuestionChange,
  onCompare,
}: CompareSidebarProps) {
  return (
    <div className="flex h-full min-h-0 flex-col bg-stone-50/80">
      <div className="border-b border-border/50 px-5 py-4">
        <h2 className="text-[10px] font-bold uppercase tracking-[0.24em] text-muted-foreground">
          {isZh ? '对比设置' : 'Compare Setup'}
        </h2>
      </div>
      <ScrollArea className="flex-1">
        <div className="flex flex-col gap-4 p-4">
          <div className="rounded-2xl border border-border/60 bg-card p-3">
            <h3 className="mb-2 font-serif text-sm font-semibold tracking-tight">
              {isZh ? '选择论文' : 'Select Papers'}
              <span className="ml-1 text-xs text-muted-foreground">({selectedPapers.length}/10)</span>
            </h3>
            {selectionNotice ? (
              <p className="mb-2 rounded-lg border border-amber-300/60 bg-amber-50 px-2 py-1.5 text-[11px] text-amber-900">
                {selectionNotice}
              </p>
            ) : null}
            <div className="flex gap-1">
              <input
                name="paperSearch"
                type="text"
                className="flex-1 rounded-lg border border-border/60 bg-background px-2 py-1 text-sm outline-none focus:border-primary/50"
                placeholder={isZh ? '搜索论文…' : 'Search papers…'}
                value={searchQuery}
                onChange={(event) => onSearchQueryChange(event.target.value)}
                onKeyDown={(event) => event.key === 'Enter' && onSearch()}
              />
              <Button size="sm" variant="outline" onClick={onSearch} disabled={searchLoading}>
                <span className="sr-only">{isZh ? '搜索论文' : 'Search papers'}</span>
                {searchLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
              </Button>
            </div>
            {searchResults.length > 0 ? (
              <ul className="mt-2 space-y-1">
                {searchResults.map((paper) => (
                  <li key={paper.id}>
                    <button
                      type="button"
                      className="flex w-full items-start gap-1 rounded-lg px-2 py-1 text-left text-sm hover:bg-muted/40"
                      onClick={() => onAddPaper(paper)}
                    >
                      <Plus className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-muted-foreground" />
                      <span className="line-clamp-2">{paper.title}</span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : null}
            {selectedPapers.length > 0 ? (
              <div className="mt-2 flex flex-wrap gap-1">
                {selectedPapers.map((paper) => (
                  <PaperChip key={paper.id} paper={paper} onRemove={() => onRemovePaper(paper.id)} />
                ))}
              </div>
            ) : null}
          </div>

          <div className="rounded-2xl border border-border/60 bg-card p-3">
            <h3 className="mb-2 font-serif text-sm font-semibold tracking-tight">{isZh ? '对比维度' : 'Dimensions'}</h3>
            <div className="flex flex-wrap gap-1.5">
              {ALLOWED_COMPARE_DIMENSIONS.map((dimId) => (
                <button
                  key={dimId}
                  type="button"
                  onClick={() => onToggleDim(dimId)}
                  className={`rounded-full border px-2 py-0.5 text-xs transition-colors ${
                    enabledDims.has(dimId)
                      ? 'border-primary/40 bg-primary/10 text-primary'
                      : 'border-border/50 text-muted-foreground'
                  }`}
                >
                  {DIMENSION_LABELS[dimId]}
                </button>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-border/60 bg-card p-3">
            <h3 className="mb-2 font-serif text-sm font-semibold tracking-tight">
              {isZh ? '研究问题（可选）' : 'Research Question (optional)'}
            </h3>
            <textarea
              name="researchQuestion"
              className="w-full resize-none rounded-lg border border-border/60 bg-background px-2 py-1.5 text-sm outline-none focus:border-primary/50"
              rows={3}
              placeholder={isZh ? '输入研究问题，引导检索…' : 'Type a question to guide retrieval…'}
              value={question}
              onChange={(event) => onQuestionChange(event.target.value)}
            />
          </div>

          <Button className="w-full" onClick={onCompare} disabled={selectedPapers.length < 2 || compareLoading}>
            {compareLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <BookOpen className="mr-2 h-4 w-4" />}
            {isZh ? '生成对比表' : 'Generate Compare Table'}
          </Button>
        </div>
      </ScrollArea>
    </div>
  );
}
