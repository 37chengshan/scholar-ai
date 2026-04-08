/**
 * CitationsPanel Component
 *
 * Right sidebar panel for displaying citations in Chat responses.
 * Shows citation details with click-to-navigate functionality.
 *
 * Features:
 * - Displays citation type badge (text, table, figure)
 * - Shows similarity score, paper title, page number
 * - Click navigates to /read/:paperId?page=N
 * - Right sidebar layout (w-80) per D-07
 *
 * Usage:
 * ```tsx
 * <CitationsPanel citations={citations} />
 * ```
 */

import { useNavigate } from 'react-router';
import { FileText, Table, Image, ExternalLink } from 'lucide-react';
import { clsx } from 'clsx';

/**
 * Citation type
 */
export type CitationType = 'text' | 'table' | 'figure';

/**
 * Citation data structure
 */
export interface Citation {
  paper_id: string;
  paper_title: string;
  page?: number;
  snippet: string;
  score: number;
  type: CitationType;
}

/**
 * CitationsPanel props
 */
export interface CitationsPanelProps {
  citations: Citation[];
  className?: string;
}

/**
 * Get icon for citation type
 */
function getCitationIcon(type: CitationType) {
  switch (type) {
    case 'table':
      return Table;
    case 'figure':
      return Image;
    case 'text':
    default:
      return FileText;
  }
}

/**
 * Get badge color for citation type
 */
function getTypeBadgeColor(type: CitationType) {
  switch (type) {
    case 'table':
      return 'bg-green-100 text-green-700';
    case 'figure':
      return 'bg-purple-100 text-purple-700';
    case 'text':
    default:
      return 'bg-blue-100 text-blue-700';
  }
}

/**
 * CitationsPanel Component
 *
 * Displays citations in a right sidebar panel.
 * Each citation shows type, score, title, page, and snippet.
 * Click navigates to the paper reader at the cited page.
 */
export function CitationsPanel({ citations, className }: CitationsPanelProps) {
  const navigate = useNavigate();

  /**
   * Handle citation click - navigate to paper page
   */
  const handleCitationClick = (citation: Citation) => {
    const page = citation.page || 1;
    navigate(`/read/${citation.paper_id}?page=${page}`);
  };

  return (
    <div
      className={clsx(
        'w-80 border-l border-border/50 bg-background flex flex-col h-full',
        className
      )}
    >
      {/* Header */}
      <div className="px-4 py-3.5 border-b border-border/50 bg-background/80 backdrop-blur-md sticky top-0 z-10">
        <div className="flex items-center justify-between">
          <h3 className="font-serif text-sm font-bold tracking-tight">
            Citations
          </h3>
          <span className="text-xs font-mono text-muted-foreground bg-muted px-2 py-0.5 rounded-sm">
            {citations.length}
          </span>
        </div>
      </div>

      {/* Citations List */}
      <div className="flex-1 overflow-y-auto p-4">
        {citations.length === 0 ? (
          <div className="text-center py-8">
            <FileText className="w-8 h-8 text-muted-foreground/30 mx-auto mb-2" />
            <p className="text-sm text-muted-foreground">
              No citations in this response
            </p>
            <p className="text-xs text-muted-foreground/60 mt-1">
              Ask a question about your papers to see sources
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {citations.map((citation, index) => {
              const Icon = getCitationIcon(citation.type);
              const badgeColor = getTypeBadgeColor(citation.type);

              return (
                <button
                  key={`${citation.paper_id}-${index}`}
                  onClick={() => handleCitationClick(citation)}
                  className="w-full text-left p-3 border border-border/50 rounded-sm cursor-pointer hover:bg-muted/50 hover:border-primary/30 transition-all duration-200 group"
                >
                  {/* Type Badge & Score */}
                  <div className="flex items-center gap-2 mb-2">
                    <span
                      className={clsx(
                        'text-xs px-2 py-0.5 rounded-sm font-bold uppercase tracking-wider flex items-center gap-1',
                        badgeColor
                      )}
                    >
                      <Icon className="w-3 h-3" />
                      {citation.type}
                    </span>
                    <span className="text-xs text-muted-foreground font-mono">
                      Score: {citation.score.toFixed(2)}
                    </span>
                    <ExternalLink className="w-3 h-3 text-muted-foreground ml-auto opacity-0 group-hover:opacity-100 transition-opacity" />
                  </div>

                  {/* Paper Title */}
                  <div className="font-medium text-sm truncate mb-1 group-hover:text-primary transition-colors">
                    {citation.paper_title}
                  </div>

                  {/* Page Number */}
                  {citation.page && (
                    <div className="text-xs text-muted-foreground mb-1.5">
                      Page {citation.page}
                    </div>
                  )}

                  {/* Snippet */}
                  <div className="text-xs text-muted-foreground/80 line-clamp-2 leading-relaxed">
                    {citation.snippet}
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

export type { CitationsPanelProps as CitationsPanelPropsType };