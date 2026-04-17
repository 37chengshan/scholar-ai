import { Search as SearchIcon } from 'lucide-react';

interface SearchToolbarProps {
  query: string;
  onQueryChange: (query: string) => void;
  placeholder: string;
  queryLabel: string;
  total?: number;
  isZh: boolean;
}

export function SearchToolbar({
  query,
  onQueryChange,
  placeholder,
  queryLabel,
  total,
  isZh,
}: SearchToolbarProps) {
  return (
    <div className="px-5 py-4 border-b border-border/50 bg-background/90 backdrop-blur-md sticky top-0 z-10 flex flex-col gap-3 shadow-sm">
      <div className="flex justify-between items-center gap-4">
        <div className="relative flex-1 max-w-2xl">
          <div className="flex items-center gap-3 bg-card border border-primary/30 p-1 rounded-full focus-within:border-primary transition-colors shadow-sm group">
            <SearchIcon className="w-4 h-4 text-primary ml-3" />
            <input
              type="text"
              value={query}
              onChange={(event) => onQueryChange(event.target.value)}
              className="flex-1 bg-transparent border-none text-sm font-serif font-bold tracking-wide focus:outline-none focus:ring-0 placeholder:font-sans placeholder:font-normal placeholder:tracking-normal placeholder:text-muted-foreground"
              placeholder={placeholder}
            />
            <button className="bg-primary text-primary-foreground px-4 py-1.5 rounded-full text-[10px] font-bold uppercase tracking-[0.2em] hover:bg-secondary transition-colors h-full shadow-sm shadow-primary/20">
              {queryLabel}
            </button>
          </div>
        </div>
        {typeof total === 'number' && (
          <div className="text-[9px] font-mono tracking-[0.2em] text-muted-foreground flex-shrink-0">
            {total.toLocaleString()} {isZh ? '条结果' : 'results'}
          </div>
        )}
      </div>
    </div>
  );
}
