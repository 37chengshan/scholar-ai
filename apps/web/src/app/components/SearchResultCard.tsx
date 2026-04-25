/**
 * SearchResultCard Component
 *
 * Displays a single search result from internal or external source
 *
 * Features:
 * - Shows title, authors, abstract, year, source
 * - Add to library button for external papers
 * - Click to view details
 */

import { Plus, ExternalLink as ExternalLinkIcon } from 'lucide-react';
import { clsx } from 'clsx';
import { Link } from 'react-router';

export interface SearchResultCardProps {
  result: {
    id: string;
    title: string;
    authors?: string[];
    abstract?: string;
    year?: number;
    source: 'internal' | 'arxiv' | 's2';
    paperId?: string;
    externalId?: string;
    pdfUrl?: string;
    citations?: number;
  };
  onAddToLibrary?: (result: any) => void;
  onViewPaper?: (paperId: string) => void;
}

export function SearchResultCard({ result, onAddToLibrary, onViewPaper }: SearchResultCardProps) {
  const isInternal = result.source === 'internal';
  const paperHref = isInternal && result.paperId ? `/read/${result.paperId}` : null;

  return (
    <div
      className="group relative flex flex-col gap-3 overflow-hidden rounded-sm border border-border/50 bg-card p-5 transition-[border-color,box-shadow] duration-300 hover:border-primary/50 hover:shadow-md"
      data-testid="search-result-card"
    >
      <div className="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-primary/0 via-primary/0 to-primary/0 group-hover:via-primary/50 transition-colors duration-500" />

      <div className="flex justify-between items-start">
        <div className="flex items-center gap-2 text-[8px] font-bold uppercase tracking-widest text-primary">
          <span className={clsx(
            "px-1.5 py-0.5 rounded-sm border",
            isInternal ? "border-primary/15 bg-primary/10" : "border-primary/10 bg-primary/[0.07] text-foreground/75"
          )}>
            {result.source === 's2' ? 'Semantic Scholar' : result.source}
          </span>
          {result.year && (
            <span className="text-muted-foreground font-mono">{result.year}</span>
          )}
        </div>
        {result.citations !== undefined && (
          <div className="flex items-center gap-1.5 text-[9px] font-bold uppercase tracking-widest text-muted-foreground">
            <div className="w-1.5 h-1.5 rounded-full bg-primary/70" />
            {result.citations}
          </div>
        )}
      </div>

      <div className="flex flex-col gap-1.5">
        {paperHref ? (
          <Link
            to={paperHref}
            className="line-clamp-2 font-serif text-xl font-black leading-tight tracking-tight transition-colors hover:text-primary focus-visible:text-primary"
          >
            {result.title}
          </Link>
        ) : (
          <h3 className="line-clamp-2 font-serif text-xl font-black leading-tight tracking-tight">
            {result.title}
          </h3>
        )}
        {result.authors && result.authors.length > 0 && (
          <p className="font-sans text-[11px] font-medium text-foreground/80 line-clamp-1 truncate">
            {result.authors.join(', ')}
          </p>
        )}
      </div>

      {result.abstract && (
        <div className="flex flex-col flex-1">
          <p className="font-serif text-xs text-foreground/70 leading-[1.6] line-clamp-3 italic border-l-2 border-primary/20 pl-3 mt-1 flex-1">
            {result.abstract}
          </p>
        </div>
      )}

      <div className="mt-3 flex flex-wrap items-center justify-between gap-3 border-t border-border/30 pt-3">
        {!isInternal && onAddToLibrary && (
          <button
            type="button"
            onClick={() => onAddToLibrary(result)}
            className="flex items-center gap-1.5 text-[9px] font-bold uppercase tracking-widest bg-primary text-primary-foreground px-3 py-1.5 rounded-sm hover:bg-secondary transition-colors shadow-sm"
            aria-label="Import paper into library"
          >
            <Plus className="w-3 h-3" /> Import
          </button>
        )}
        {paperHref && (
          <Link
            to={paperHref}
            className="flex items-center gap-1.5 rounded-sm bg-primary px-3 py-1.5 text-[9px] font-bold uppercase tracking-widest text-primary-foreground shadow-sm transition-colors hover:bg-secondary"
          >
            View
          </Link>
        )}
        {!paperHref && isInternal && result.paperId && onViewPaper && (
          <button
            type="button"
            onClick={() => onViewPaper(result.paperId!)}
            className="flex items-center gap-1.5 rounded-sm bg-primary px-3 py-1.5 text-[9px] font-bold uppercase tracking-widest text-primary-foreground shadow-sm transition-colors hover:bg-secondary"
          >
            View
          </button>
        )}
        <div className="flex items-center gap-2">
          {!isInternal && result.pdfUrl && (
            <a
              href={result.pdfUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-[9px] font-bold uppercase tracking-widest text-foreground/60 hover:text-primary transition-colors px-2 py-1"
            >
              <ExternalLinkIcon className="w-3 h-3" /> PDF
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
