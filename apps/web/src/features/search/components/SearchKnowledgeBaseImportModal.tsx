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
  importingPaperId: string | null;
  labels: {
    title: string;
    loading: string;
    empty: string;
    papersUnit: string;
  };
  onClose: () => void;
  onConfirmImport: (kbId: string) => void;
}

export function SearchKnowledgeBaseImportModal({
  open,
  loadingKnowledgeBases,
  knowledgeBases,
  importingPaperId,
  labels,
  onClose,
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
        className="bg-card border border-border rounded-lg shadow-xl w-full max-w-md"
      >
        <div className="px-6 py-4 border-b border-border flex items-center justify-between">
          <h3 className="font-serif font-bold text-lg">{labels.title}</h3>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground">✕</button>
        </div>
        <div className="p-6 space-y-3">
          {loadingKnowledgeBases ? (
            <div className="flex items-center justify-center py-4">
              <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">{labels.loading}</div>
            </div>
          ) : knowledgeBases.length > 0 ? (
            knowledgeBases.map((kb) => (
              <button
                key={kb.id}
                onClick={() => onConfirmImport(kb.id)}
                disabled={importingPaperId !== null}
                className={clsx(
                  'w-full p-4 border border-border/50 rounded-sm hover:border-primary/50 transition-colors text-left',
                  importingPaperId !== null && 'opacity-50 cursor-not-allowed'
                )}
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
      </motion.div>
    </div>
  );
}
