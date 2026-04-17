interface SearchPaginationProps {
  hasPrev: boolean;
  hasMore: boolean;
  loading: boolean;
  page: number;
  totalPages: number;
  prevPage: () => void;
  nextPage: () => void;
  labels: {
    prevPage: string;
    nextPage: string;
    page: string;
    of: string;
  };
}

export function SearchPagination({
  hasPrev,
  hasMore,
  loading,
  page,
  totalPages,
  prevPage,
  nextPage,
  labels,
}: SearchPaginationProps) {
  return (
    <div className="flex justify-center items-center gap-4 mt-8 pt-6 border-t border-border/50">
      <button
        onClick={prevPage}
        disabled={!hasPrev || loading}
        className="px-4 py-2 bg-card border border-border rounded-sm text-[10px] font-bold uppercase tracking-widest hover:bg-muted disabled:opacity-40 disabled:cursor-not-allowed transition-colors shadow-sm"
      >
        {labels.prevPage}
      </button>
      <div className="flex items-center gap-2 px-4 py-2 bg-muted/30 rounded-sm">
        <span className="text-[11px] font-mono text-muted-foreground">{labels.page}</span>
        <span className="text-[14px] font-bold text-primary">{page + 1}</span>
        <span className="text-[11px] font-mono text-muted-foreground">{labels.of}</span>
        <span className="text-[14px] font-bold text-foreground">{totalPages}</span>
      </div>
      <button
        onClick={nextPage}
        disabled={!hasMore || loading}
        className="px-4 py-2 bg-primary text-primary-foreground border border-primary rounded-sm text-[10px] font-bold uppercase tracking-widest hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors shadow-sm"
      >
        {labels.nextPage}
      </button>
    </div>
  );
}
