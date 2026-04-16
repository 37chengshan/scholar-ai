/**
 * AuthorResultCard Component
 *
 * Displays author search results with academic impact metrics.
 *
 * Features:
 * - Hover effects with visual feedback
 * - Click handler for author selection
 * - Academic metrics display
 *
 * Per D-06: Display hIndex, citationCount, paperCount
 */

import { Award, BookOpen, FileText } from 'lucide-react';
import { AuthorSearchResult } from '@/services/searchApi';

interface AuthorResultCardProps {
  author: AuthorSearchResult;
  onClick?: (author: AuthorSearchResult) => void;
}

export function AuthorResultCard({ author, onClick }: AuthorResultCardProps) {
  return (
    <div
      onClick={() => onClick?.(author)}
      className="p-5 border border-border/50 bg-card rounded-sm flex flex-col gap-3 group hover:border-primary/50 hover:shadow-md transition-all cursor-pointer relative overflow-hidden"
    >
      <div className="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-primary/0 via-primary/0 to-primary/0 group-hover:via-primary/50 transition-colors duration-500" />

      {/* Author Name */}
      <h3 className="font-serif font-black text-lg leading-tight group-hover:text-primary transition-colors tracking-tight">
        {author.name}
      </h3>

      {/* D-06: Metrics: hIndex, citations, papers */}
      <div className="flex gap-4 text-xs">
        {author.hIndex !== undefined && (
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <Award className="w-3.5 h-3.5 text-primary" />
            <span className="font-bold">{author.hIndex}</span>
            <span className="text-muted-foreground/70">h-index</span>
          </div>
        )}
        {author.citationCount !== undefined && (
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <BookOpen className="w-3.5 h-3.5 text-secondary" />
            <span className="font-bold">{author.citationCount.toLocaleString()}</span>
            <span className="text-muted-foreground/70">citations</span>
          </div>
        )}
        {author.paperCount !== undefined && (
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <FileText className="w-3.5 h-3.5" />
            <span className="font-bold">{author.paperCount}</span>
            <span className="text-muted-foreground/70">papers</span>
          </div>
        )}
      </div>

      {/* Author ID (small, muted) */}
      <div className="text-[9px] font-mono text-muted-foreground/50">
        ID: {author.authorId}
      </div>
    </div>
  );
}