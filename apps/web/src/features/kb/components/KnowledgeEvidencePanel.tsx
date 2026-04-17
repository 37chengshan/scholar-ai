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
          <Search className="h-6 w-6 text-zinc-400" />
        </div>
        <input
          type="text"
          className="block w-full pl-12 pr-32 py-5 text-lg border-2 border-zinc-900 font-medium placeholder:text-zinc-400 focus:outline-none focus:ring-0 focus:border-primary shadow-[6px_6px_0px_0px_rgba(24,24,27,1)] transition-colors bg-white"
          placeholder="输入您的问题..."
          value={searchQuery}
          onChange={(event) => onSearchQueryChange(event.target.value)}
        />
        <button
          type="submit"
          disabled={isSearching || !searchQuery.trim()}
          className="absolute right-2 top-2 bottom-2 bg-primary hover:bg-zinc-900 text-white px-6 font-bold uppercase tracking-wider transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {isSearching ? <Loader2 className="w-5 h-5 animate-spin" /> : '检索'}
        </button>
      </form>

      {papersEmpty ? (
        <div className="bg-white border-2 border-zinc-900 p-8 text-center text-zinc-600 font-medium shadow-[8px_8px_0px_0px_rgba(24,24,27,1)]">
          请先向知识库导入论文，再开始检索。
        </div>
      ) : null}

      {results && results.length > 0 ? (
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
              onClick={() => onOpenPaper(result.paperId, result.page)}
            >
              <div className="absolute -left-2 -top-2 bg-orange-100 text-orange-800 border-2 border-orange-200 font-mono text-xs px-2 py-1 font-bold shadow-sm">
                相关度: {(result.score * 100).toFixed(1)}%
              </div>
              <p className="text-lg text-zinc-800 mt-4 leading-relaxed font-serif">"...{result.content}..."</p>
              <div className="mt-6 flex items-center gap-2 text-sm font-medium text-zinc-500 bg-zinc-50 p-3 border border-zinc-100">
                <span className="truncate">{result.paperTitle || result.paperId}</span>
                {result.page ? <span className="text-primary">第{result.page}页</span> : null}
              </div>
            </div>
          ))}
        </div>
      ) : null}

      {results && results.length === 0 ? (
        <div className="bg-white border-2 border-zinc-900 p-8 text-center text-zinc-600 font-medium shadow-[8px_8px_0px_0px_rgba(24,24,27,1)]">
          没有检索到相关结果，请尝试其他问题。
        </div>
      ) : null}
    </div>
  );
}
