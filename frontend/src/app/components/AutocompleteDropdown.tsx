/**
 * AutocompleteDropdown Component
 *
 * Displays autocomplete suggestions for paper search.
 *
 * Features:
 * - Framer Motion animations
 * - Loading state indicator
 * - Empty state message
 * - Bilingual support (EN/ZH)
 *
 * Per D-02: Display title + authors + year
 * Per D-03: Show up to 5 results
 */

import { motion, AnimatePresence } from 'motion/react';
import { AutocompletePaper } from '@/services/searchApi';
import { useLanguage } from '../contexts/LanguageContext';

interface AutocompleteDropdownProps {
  results: AutocompletePaper[];
  loading: boolean;
  visible: boolean;
  onSelect: (paper: AutocompletePaper) => void;
}

export function AutocompleteDropdown({
  results,
  loading,
  visible,
  onSelect,
}: AutocompleteDropdownProps) {
  const { language } = useLanguage();
  const isZh = language === 'zh';

  const t = {
    loading: isZh ? '搜索中...' : 'Searching...',
    noResults: isZh ? '未找到论文' : 'No papers found',
  };

  if (!visible) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -10 }}
        className="absolute top-full left-0 right-0 mt-2 bg-card border border-border rounded-lg shadow-lg z-50 max-h-80 overflow-y-auto"
      >
        {loading && (
          <div className="px-4 py-3 text-sm text-muted-foreground">
            {t.loading}
          </div>
        )}

        {!loading && results.length === 0 && (
          <div className="px-4 py-3 text-sm text-muted-foreground">
            {t.noResults}
          </div>
        )}

        {!loading &&
          results.map((paper, index) => (
            <button
              key={paper.paperId || index}
              onClick={() => onSelect(paper)}
              className="w-full px-4 py-3 text-left hover:bg-muted transition-colors border-b border-border/50 last:border-0"
            >
              {/* D-02: Title + Authors + Year */}
              <div className="font-serif font-bold text-sm text-foreground line-clamp-1">
                {paper.title}
              </div>
              {paper.authors && paper.authors.length > 0 && (
                <div className="text-xs text-muted-foreground mt-1 line-clamp-1">
                  {paper.authors.slice(0, 3).map((a) => a.name).join(', ')}
                  {paper.authors.length > 3 && ' et al.'}
                </div>
              )}
              {paper.year && (
                <div className="text-xs text-muted-foreground/70 mt-0.5 font-mono">
                  {paper.year}
                </div>
              )}
            </button>
          ))}
      </motion.div>
    </AnimatePresence>
  );
}