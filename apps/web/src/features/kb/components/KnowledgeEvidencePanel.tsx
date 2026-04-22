import { Loader2, Search } from 'lucide-react';
import type { KBSearchResult } from '@/services/kbApi';

interface KnowledgeEvidencePanelProps {
  searchQuery: string;
  isSearching: boolean;
  results: KBSearchResult[] | null;
  papersEmpty: boolean;
  onSearchQueryChange: (value: string) => void;
  onSearchSubmit: () => void;
  onOpenPaper: (paperId: string, page?: number | null) => void;
}

export function KnowledgeEvidencePanel({
  searchQuery,
  isSearching,
  results,
  papersEmpty,
  onSearchQueryChange,
  onSearchSubmit,
  onOpenPaper,
}: KnowledgeEvidencePanelProps) {
  return (
    <div className="space-y-8 max-w-4xl">
      <form
        onSubmit={(event) => {
          event.preventDefault();
          onSearchSubmit();
        }}
        className="relative max-w-3xl"
      >
        <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
          <Search className="h-6 w-6 text-muted-foreground" />
        </div>
        <input
          type="text"
          className="block w-full bg-paper-1 py-5 pl-12 pr-32 text-lg font-medium border border-border/80 placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-0 transition-colors"
          placeholder="输入您的问题..."
          value={searchQuery}
          onChange={(event) => onSearchQueryChange(event.target.value)}
        />
        <button
          type="submit"
          disabled={isSearching || !searchQuery.trim()}
          className="absolute bottom-2 right-2 top-2 flex items-center gap-2 bg-primary px-6 font-bold uppercase tracking-wider text-white transition-colors hover:bg-secondary disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isSearching ? <Loader2 className="w-5 h-5 animate-spin" /> : '检索'}
        </button>
      </form>

      {papersEmpty ? (
        <div className="border border-border/80 bg-paper-1 p-8 text-center font-medium text-muted-foreground">
          请先向知识库导入论文，再开始检索。
        </div>
      ) : null}

      {results && results.length > 0 ? (
        <div className="space-y-6 max-w-4xl">
          <div className="flex items-center gap-4 mb-8">
            <div className="h-px bg-border flex-1"></div>
            <span className="px-4 text-sm font-bold uppercase tracking-widest text-muted-foreground">
              检索到 {results.length} 个相关片段
            </span>
            <div className="h-px bg-border flex-1"></div>
          </div>

          {results.map((result) => (
            <div
              key={result.id}
              className="group relative cursor-pointer border border-border/80 bg-paper-1 p-6 transition-colors hover:border-primary/40 hover:bg-primary/[0.03]"
              onClick={() => onOpenPaper(result.paperId, result.page)}
            >
              <div className="absolute -left-2 -top-2 border border-primary/20 bg-primary/[0.08] px-2 py-1 font-mono text-xs font-bold text-primary">
                相关度: {(result.score * 100).toFixed(1)}%
              </div>
              <p className="mt-4 text-lg leading-relaxed font-serif text-foreground">"...{result.content}..."</p>
              <div className="mt-6 flex items-center gap-2 border border-border/70 bg-paper-2 p-3 text-sm font-medium text-muted-foreground">
                <span className="truncate">{result.paperTitle || result.paperId}</span>
                {result.page ? <span className="text-primary">第{result.page}页</span> : null}
              </div>
            </div>
          ))}
        </div>
      ) : null}

      {results && results.length === 0 ? (
        <div className="border border-border/80 bg-paper-1 p-8 text-center font-medium text-muted-foreground">
          没有检索到相关结果，请尝试其他问题。
        </div>
      ) : null}
    </div>
  );
}
