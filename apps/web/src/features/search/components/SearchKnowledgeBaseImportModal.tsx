import { clsx } from 'clsx';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/app/components/ui/dialog';

interface KnowledgeBaseItem {
  id: string;
  name: string;
  paperCount?: number;
}

interface SearchKnowledgeBaseImportModalProps {
  open: boolean;
  loadingKnowledgeBases: boolean;
  knowledgeBases: KnowledgeBaseItem[];
  selectedKnowledgeBaseId: string | null;
  importingPaperId: string | null;
  labels: {
    title: string;
    loading: string;
    empty: string;
    papersUnit: string;
    confirm: string;
    selectPrompt: string;
  };
  onClose: () => void;
  onSelectKnowledgeBase: (kbId: string) => void;
  onConfirmImport: () => void;
}

export function SearchKnowledgeBaseImportModal({
  open,
  loadingKnowledgeBases,
  knowledgeBases,
  selectedKnowledgeBaseId,
  importingPaperId,
  labels,
  onClose,
  onSelectKnowledgeBase,
  onConfirmImport,
}: SearchKnowledgeBaseImportModalProps) {
  if (!open) {
    return null;
  }

  return (
    <Dialog open={open} onOpenChange={(nextOpen) => { if (!nextOpen) onClose(); }}>
      <DialogContent className="flex max-h-[min(80vh,42rem)] w-full max-w-md flex-col p-0">
        <DialogHeader className="border-b border-border px-6 py-4 text-left">
          <DialogTitle className="font-serif text-lg font-bold">{labels.title}</DialogTitle>
          <DialogDescription className="text-xs text-muted-foreground">
            {labels.selectPrompt}
          </DialogDescription>
        </DialogHeader>
        <div className="p-6 space-y-3 overflow-y-auto">
          {loadingKnowledgeBases ? (
            <div className="flex items-center justify-center py-4">
              <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">{labels.loading}</div>
            </div>
          ) : knowledgeBases.length > 0 ? (
            knowledgeBases.map((kb) => (
              <button
                key={kb.id}
                type="button"
                onClick={() => onSelectKnowledgeBase(kb.id)}
                disabled={importingPaperId !== null}
                className={clsx(
                  'w-full p-4 border rounded-sm transition-colors text-left',
                  selectedKnowledgeBaseId === kb.id
                    ? 'border-primary bg-primary/5 shadow-sm'
                    : 'border-border/50 hover:border-primary/50',
                  importingPaperId !== null && 'opacity-50 cursor-not-allowed'
                )}
                aria-pressed={selectedKnowledgeBaseId === kb.id}
              >
                <div className="font-semibold text-sm mb-1">{kb.name}</div>
                <div className="text-xs text-muted-foreground">
                  {kb.paperCount || 0} {labels.papersUnit}
                </div>
              </button>
            ))
          ) : (
            <div className="text-sm text-muted-foreground text-center py-4">{labels.empty}</div>
          )}
        </div>
        <div className="border-t border-border px-6 py-4">
          <button
            type="button"
            onClick={onConfirmImport}
            disabled={!selectedKnowledgeBaseId || importingPaperId !== null || loadingKnowledgeBases}
            className={clsx(
              'w-full rounded-sm px-4 py-2 text-sm font-semibold transition-colors',
              !selectedKnowledgeBaseId || importingPaperId !== null || loadingKnowledgeBases
                ? 'cursor-not-allowed bg-muted text-muted-foreground'
                : 'bg-primary text-primary-foreground hover:bg-primary/90'
            )}
          >
            {labels.confirm}
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
