import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/app/components/ui/dialog';
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
    source: 'semantic_scholar';
    externalId: string;
    s2PaperId: string;
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
    <Dialog open={open} onOpenChange={(nextOpen) => { if (!nextOpen) onClose(); }}>
      <DialogContent className="w-full max-w-2xl overflow-hidden p-0">
        <DialogHeader className="border-b border-border px-6 py-4 text-left">
          <DialogTitle className="font-serif text-lg font-bold">
            {selectedAuthor?.name} ({authorPapers.length})
          </DialogTitle>
          <DialogDescription className="text-xs text-muted-foreground">
            Browse this author&apos;s papers and import one into your knowledge base.
          </DialogDescription>
        </DialogHeader>
        <div className="max-h-[60vh] overflow-y-auto p-6 space-y-3">
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
                    source: 'semantic_scholar',
                    externalId: paper.paperId,
                    s2PaperId: paper.paperId,
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
      </DialogContent>
    </Dialog>
  );
}
