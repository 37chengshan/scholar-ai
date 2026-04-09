/**
 * CitationsPanel Component (Enhanced - Phase 28-03)
 *
 * Displays citations with inline markers and collapsible bottom panel.
 * Per D-05: inline [1][2] markers + collapsible panel with relevance scores.
 *
 * Features:
 * - Inline citation markers as clickable sup badges
 * - Collapsible bottom panel showing top 3 by default
 * - "Show all" button when > 3 citations
 * - Relevance badges colored by score (green/yellow/gray)
 * - Bilingual labels via useLanguage()
 * - motion/react animation for expand/collapse
 *
 * Usage:
 * ```tsx
 * <CitationsPanel citations={citations} />
 * ```
 */

import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { useNavigate } from 'react-router';
import { FileText, Table, Image, ChevronDown, ChevronUp, ExternalLink } from 'lucide-react';
import { clsx } from 'clsx';
import { useLanguage } from '../contexts/LanguageContext';
import { PaperCitation } from '@/types/chat';

/**
 * CitationsPanel props
 */
export interface CitationsPanelProps {
  citations: PaperCitation[];
  className?: string;
}

/**
 * Get icon for citation content type
 */
function getCitationIcon(contentType: PaperCitation['content_type']) {
  switch (contentType) {
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
 * Get relevance badge color based on score (0-1)
 * Per UI-SPEC: > 80% = green, 60-80% = yellow, < 60% = gray
 */
function getRelevanceBadgeColor(score: number) {
  if (score > 0.8) return 'bg-green-100 text-green-700';
  if (score >= 0.6) return 'bg-yellow-100 text-yellow-700';
  return 'bg-gray-100 text-gray-600';
}

/**
 * Format relevance score as percentage
 */
function formatRelevance(score: number): string {
  return `${Math.round(score * 100)}%`;
}

/**
 * Render inline citation markers in message text.
 * Replaces [1], [2], etc. with clickable sup badges.
 */
export function renderContentWithCitations(
  content: string,
  onCitationClick: (index: number) => void
): React.ReactNode {
  const citationRegex = /\[(\d+)\]/g;
  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let match;

  while ((match = citationRegex.exec(content)) !== null) {
    // Add text before the citation marker
    if (match.index > lastIndex) {
      parts.push(content.slice(lastIndex, match.index));
    }

    // Add citation badge
    const citationNum = parseInt(match[1], 10);
    parts.push(
      <sup
        key={`cite-${match.index}`}
        className="inline-flex items-center justify-center w-5 h-5 text-xs bg-primary/10 text-primary rounded cursor-pointer hover:bg-primary/20 font-mono align-super"
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          onCitationClick(citationNum - 1); // 0-based index
        }}
      >
        {citationNum}
      </sup>
    );

    lastIndex = match.index + match[0].length;
  }

  // Add remaining text
  if (lastIndex < content.length) {
    parts.push(content.slice(lastIndex));
  }

  return parts.length > 0 ? parts : content;
}

/**
 * CitationsPanel Component
 *
 * Collapsible panel showing citation cards with relevance scores.
 * Default: top 3 citations. "Show all" button if > 3.
 */
export function CitationsPanel({ citations, className }: CitationsPanelProps) {
  const navigate = useNavigate();
  const { language } = useLanguage();
  const isZh = language === 'zh';
  const [expanded, setExpanded] = useState(false);

  if (citations.length === 0) return null;

  const displayCount = expanded ? citations.length : Math.min(3, citations.length);
  const visibleCitations = citations.slice(0, displayCount);
  const hasMore = citations.length > 3;

  const handleCitationClick = (citation: PaperCitation) => {
    const page = citation.page || 1;
    navigate(`/read/${citation.paper_id}?page=${page}`);
  };

  const headerLabel = isZh
    ? `${citations.length} 个引用来源`
    : `${citations.length} source${citations.length > 1 ? 's' : ''}`;

  const toggleLabel = expanded
    ? (isZh ? '收起' : 'Collapse')
    : (isZh ? `显示全部 ${citations.length} 个引用` : `Show all ${citations.length} sources`);

  return (
    <div
      className={clsx(
        'border-t border-border/50 pt-3 mt-3',
        className
      )}
    >
      {/* Header with toggle */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center justify-between w-full text-left group"
      >
        <h4 className="text-xs font-semibold text-muted-foreground">
          {headerLabel}
        </h4>
        <span className="flex items-center gap-1 text-xs text-muted-foreground group-hover:text-foreground transition-colors">
          {hasMore || expanded ? toggleLabel : null}
          {expanded ? (
            <ChevronUp className="w-3 h-3" />
          ) : (
            <ChevronDown className="w-3 h-3" />
          )}
        </span>
      </button>

      {/* Citation Cards */}
      <div className="space-y-2 mt-2">
        <AnimatePresence initial={false}>
          {visibleCitations.map((citation, index) => {
            const Icon = getCitationIcon(citation.content_type);
            const relevanceColor = getRelevanceBadgeColor(citation.score);
            const authors = citation.authors.length > 0
              ? (citation.authors.length > 2
                ? `${citation.authors[0]} et al.`
                : citation.authors.join(', '))
              : '';

            return (
              <motion.button
                key={`${citation.paper_id}-${index}`}
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.2 }}
                onClick={() => handleCitationClick(citation)}
                className={clsx(
                  'w-full text-left p-3 rounded-lg border border-border/50 bg-muted/30',
                  'hover:bg-muted/50 transition-colors group'
                )}
              >
                {/* Header: Icon + Title + Relevance */}
                <div className="flex items-start gap-2">
                  <Icon className="w-3.5 h-3.5 text-muted-foreground mt-0.5 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium truncate group-hover:text-primary transition-colors">
                      {citation.title}
                    </div>
                    {authors && (
                      <div className="text-xs text-muted-foreground mt-0.5">
                        {authors} {citation.year ? `(${citation.year})` : ''}
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-1.5 flex-shrink-0">
                    <span className={clsx(
                      'text-xs px-1.5 py-0.5 rounded-full font-mono',
                      relevanceColor
                    )}>
                      {formatRelevance(citation.score)}
                    </span>
                    <ExternalLink className="w-3 h-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                  </div>
                </div>

                {/* Snippet */}
                {citation.snippet && (
                  <div className="text-xs text-muted-foreground line-clamp-2 mt-1 leading-relaxed">
                    {citation.snippet}
                  </div>
                )}
              </motion.button>
            );
          })}
        </AnimatePresence>
      </div>

      {/* Show all / Collapse button */}
      {hasMore && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full text-center text-xs text-primary hover:text-primary/80 transition-colors mt-2 py-1"
        >
          {toggleLabel}
        </button>
      )}
    </div>
  );
}
