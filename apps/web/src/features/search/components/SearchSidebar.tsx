import { Globe } from 'lucide-react';
import { clsx } from 'clsx';
import { motion } from 'motion/react';

interface SourceItem {
  id: string;
  name: string;
  statusType: 'Connected' | 'Rate Limited' | 'Disconnected';
  results: number;
}

interface SearchSidebarProps {
  activeSource: string;
  setActiveSource: (sourceId: string) => void;
  sources: SourceItem[];
  allResults: number;
  labels: {
    sources: string;
    global: string;
    aggregators: string;
    allSources: string;
    connectors: string;
  };
}

export function SearchSidebar({
  activeSource,
  setActiveSource,
  sources,
  allResults,
  labels,
}: SearchSidebarProps) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.5 }}
      className="w-[220px] border-r border-border/50 flex flex-col h-full bg-muted/20 flex-shrink-0"
    >
      <div className="px-5 py-4 border-b border-border/50 bg-background/80 backdrop-blur-md sticky top-0 z-10 flex justify-between items-center">
        <h2 className="font-serif text-xl font-black tracking-tight leading-none mb-1">{labels.sources}</h2>
        <p className="text-[8px] font-bold tracking-[0.2em] uppercase text-primary">{labels.global}</p>
      </div>

      <div className="flex-1 overflow-y-auto py-5 flex flex-col gap-6 px-4">
        <div>
          <div className="text-[9px] font-bold tracking-[0.2em] uppercase text-muted-foreground mb-3 px-1 border-b border-border/50 pb-1.5">{labels.aggregators}</div>
          <button
            onClick={() => setActiveSource('all')}
            className={clsx(
              'flex items-center gap-2.5 px-2 py-2 rounded-sm transition-colors group w-full',
              activeSource === 'all' ? 'bg-primary text-primary-foreground shadow-sm shadow-primary/20' : 'hover:bg-muted text-foreground/80 hover:text-primary'
            )}
          >
            <Globe className={clsx('w-3.5 h-3.5', activeSource === 'all' ? 'text-primary-foreground' : 'text-primary')} />
            <span className="text-[10px] font-bold uppercase tracking-widest flex-1 text-left">{labels.allSources}</span>
            <span className={clsx('text-[9px] font-mono', activeSource === 'all' ? 'text-primary-foreground/70' : 'text-muted-foreground')}>
              {allResults}
            </span>
          </button>
        </div>

        <div>
          <div className="text-[9px] font-bold tracking-[0.2em] uppercase text-muted-foreground mb-3 px-1 border-b border-border/50 pb-1.5">{labels.connectors}</div>
          <div className="flex flex-col gap-0.5">
            {sources.map((source) => (
              <button
                key={source.id}
                onClick={() => setActiveSource(source.id)}
                className={clsx(
                  'flex items-center gap-2.5 px-2 py-2 rounded-sm transition-colors group w-full',
                  activeSource === source.id ? 'bg-primary text-primary-foreground shadow-sm shadow-primary/20' : 'hover:bg-muted text-foreground/80 hover:text-primary'
                )}
              >
                <div
                  className={clsx(
                    'w-1.5 h-1.5 rounded-full flex-shrink-0',
                    source.statusType === 'Connected' && 'bg-[var(--color-status-completed)]',
                    source.statusType === 'Rate Limited' && 'bg-[var(--color-status-processing)]',
                    source.statusType === 'Disconnected' && 'bg-[var(--color-status-failed)]'
                  )}
                />
                <span className="text-[10px] font-bold uppercase tracking-widest flex-1 text-left truncate">{source.name}</span>
                {source.results > 0 && (
                  <span className={clsx('text-[9px] font-mono', activeSource === source.id ? 'text-primary-foreground/70' : 'text-muted-foreground')}>
                    {source.results}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
