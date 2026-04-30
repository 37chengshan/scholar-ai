import { motion } from 'motion/react';
import { clsx } from 'clsx';

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
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-card border border-border rounded-lg shadow-xl w-full max-w-md max-h-[min(80vh,42rem)] flex flex-col"
      >
        <div className="px-6 py-4 border-b border-border flex items-center justify-between">
          <h3 className="font-serif font-bold text-lg">{labels.title}</h3>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground">✕</button>
        </div>
        <div className="px-6 pt-4 text-xs text-muted-foreground">{labels.selectPrompt}</div>
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
      </motion.div>
    </div>
  );
}
