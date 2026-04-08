/**
 * ExpandableCitation Component
 *
 * Inline expandable citation cards that show source details on click.
 * Displays superscript number [N] that expands to show paper info.
 *
 * Part of Agent-Native architecture (D-17)
 */

import { useState } from 'react';
import { useNavigate } from 'react-router';
import { motion, AnimatePresence } from 'motion/react';
import { ExternalLink, FileText, Hash, Percent } from 'lucide-react';
import { clsx } from 'clsx';
import { useLanguage } from '../contexts/LanguageContext';

/**
 * Citation data
 */
export interface Citation {
  paperId: string;
  paperTitle: string;
  page?: number;
  snippet: string;
  similarity: number; // 0-1
}

/**
 * ExpandableCitation props
 */
export interface ExpandableCitationProps {
  citation: Citation;
  index: number; // Citation number [1], [2], etc.
  className?: string;
}

/**
 * Format similarity score as percentage
 */
function formatSimilarity(score: number): string {
  return `${(score * 100).toFixed(0)}%`;
}

/**
 * ExpandableCitation Component
 *
 * Renders a superscript citation number that expands on click
 * to show paper details with navigation link.
 */
export function ExpandableCitation({
  citation,
  index,
  className,
}: ExpandableCitationProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const navigate = useNavigate();
  const { language } = useLanguage();
  const isZh = language === 'zh';

  const t = {
    page: isZh ? '页' : 'Page',
    similarity: isZh ? '相似度' : 'Similarity',
    viewSource: isZh ? '查看原文' : 'View Source',
  };

  const handleNavigate = () => {
    const page = citation.page || 1;
    navigate(`/read/${citation.paperId}?page=${page}`);
  };

  return (
    <span className={clsx('relative inline', className)}>
      {/* Superscript number */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="inline-flex items-center justify-center min-w-[1.25rem] h-5 px-1 text-xs font-bold rounded bg-primary/20 text-primary hover:bg-primary/30 transition-colors cursor-pointer"
      >
        [{index}]
      </button>

      {/* Expandable popover */}
      <AnimatePresence>
        {isExpanded && (
          <>
            {/* Backdrop */}
            <button
              onClick={() => setIsExpanded(false)}
              className="fixed inset-0 z-40"
              aria-label="Close"
            />

            {/* Popover */}
            <motion.div
              initial={{ opacity: 0, y: -10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -10, scale: 0.95 }}
              transition={{ duration: 0.15 }}
              className="absolute z-50 left-0 top-full mt-2 w-80 bg-popover border border-border rounded-lg shadow-lg overflow-hidden"
            >
              {/* Header */}
              <div className="px-4 py-3 bg-muted/50 border-b border-border">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-primary" />
                    <span className="text-xs font-bold text-primary">
                      [{index}]
                    </span>
                  </div>
                  <button
                    onClick={handleNavigate}
                    className="flex items-center gap-1 text-xs text-primary hover:underline"
                  >
                    {t.viewSource}
                    <ExternalLink className="w-3 h-3" />
                  </button>
                </div>
              </div>

              {/* Content */}
              <div className="p-4 space-y-3">
                {/* Paper title */}
                <div>
                  <button
                    onClick={handleNavigate}
                    className="text-sm font-medium text-foreground hover:text-primary text-left transition-colors line-clamp-2"
                  >
                    {citation.paperTitle}
                  </button>
                </div>

                {/* Page number */}
                {citation.page && (
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Hash className="w-3 h-3" />
                    <span>
                      {t.page} {citation.page}
                    </span>
                  </div>
                )}

                {/* Snippet */}
                <div className="text-xs text-muted-foreground bg-muted/30 rounded-sm p-2 line-clamp-4">
                  {citation.snippet}
                </div>

                {/* Similarity score */}
                <div className="flex items-center gap-2">
                  <Percent className="w-3 h-3 text-muted-foreground" />
                  <div className="flex-1">
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="text-muted-foreground">{t.similarity}</span>
                      <span className="font-medium text-primary">
                        {formatSimilarity(citation.similarity)}
                      </span>
                    </div>
                    <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${citation.similarity * 100}%` }}
                        transition={{ duration: 0.3, delay: 0.1 }}
                        className="h-full bg-primary rounded-full"
                      />
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </span>
  );
}

/**
 * CitationRenderer Component
 *
 * Renders text with inline citations.
 * Usage:
 * ```tsx
 * <CitationRenderer text="This is supported by [1] and [2]." citations={[c1, c2]} />
 * ```
 */
export function CitationRenderer({
  text,
  citations,
  className,
}: {
  text: string;
  citations: Citation[];
  className?: string;
}) {
  // Create a map for quick citation lookup
  const citationMap = new Map<number, Citation>();
  citations.forEach((c, idx) => {
    citationMap.set(idx + 1, c);
  });

  // Split text by citation markers [N]
  const parts = text.split(/(\[\d+\])/g);

  return (
    <span className={clsx('inline', className)}>
      {parts.map((part, idx) => {
        const match = part.match(/\[(\d+)\]/);
        if (match) {
          const citationNum = parseInt(match[1], 10);
          const citation = citationMap.get(citationNum);
          if (citation) {
            return (
              <ExpandableCitation
                key={idx}
                citation={citation}
                index={citationNum}
              />
            );
          }
        }
        return <span key={idx}>{part}</span>;
      })}
    </span>
  );
}

export type { ExpandableCitationProps as ExpandableCitationPropsType };