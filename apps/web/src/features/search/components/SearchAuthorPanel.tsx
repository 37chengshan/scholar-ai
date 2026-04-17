import { motion } from 'motion/react';
import { AuthorPaper, AuthorSearchResult } from '@/services/searchApi';

interface SearchAuthorPanelProps {
  open: boolean;
  selectedAuthor: AuthorSearchResult | null;
  authorPapers: AuthorPaper[];
  loadingAuthorPapers: boolean;
  labels: {
    searching: string;
    importLabel: string;
    emptyText: string;
    citations: string;
  };
  onClose: () => void;
  onImportPaper: (paper: {
    id: string;
    title: string;
    year?: number;
    source: 's2';
    externalId: string;
  }) => void;
}

export function SearchAuthorPanel({
  open,
  selectedAuthor,
  authorPapers,
  loadingAuthorPapers,
  labels,
  onClose,
  onImportPaper,
}: SearchAuthorPanelProps) {
  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-card border border-border rounded-lg shadow-xl w-full max-w-2xl max-h-[80vh] overflow-hidden"
      >
        <div className="px-6 py-4 border-b border-border flex items-center justify-between">
          <h3 className="font-serif font-bold text-lg">
            {selectedAuthor?.name} ({authorPapers.length})
          </h3>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground">✕</button>
        </div>
        <div className="overflow-y-auto p-6 space-y-3 max-h-[60vh]">
          {loadingAuthorPapers ? (
            <div className="flex items-center justify-center py-8">
              <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
                {labels.searching}
              </div>
            </div>
          ) : authorPapers.length > 0 ? (
            authorPapers.map((paper) => (
              <div key={paper.paperId} className="p-4 border border-border/50 rounded-sm hover:border-primary/50 transition-colors">
                <h4 className="font-semibold text-sm mb-2">{paper.title}</h4>
                <div className="flex items-center gap-3 text-xs text-muted-foreground mb-3">
                  {paper.year && <span>{paper.year}</span>}
                  {paper.citationCount && <span>{labels.citations}: {paper.citationCount}</span>}
                </div>
                <button
                  onClick={() => onImportPaper({
                    id: paper.paperId,
                    title: paper.title,
                    year: paper.year,
                    source: 's2',
                    externalId: paper.paperId,
                  })}
                  className="px-3 py-1 bg-primary text-primary-foreground rounded-sm text-[9px] font-bold uppercase tracking-[0.1em] hover:bg-primary/90 transition-colors"
                >
                  {labels.importLabel}
                </button>
              </div>
            ))
          ) : (
            <div className="flex items-center justify-center py-8">
              <div className="text-sm text-muted-foreground">{labels.emptyText}</div>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}
