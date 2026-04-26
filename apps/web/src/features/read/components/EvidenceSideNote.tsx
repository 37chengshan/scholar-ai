interface EvidenceSideNoteProps {
  source: string;
  sourceId: string;
  page: number;
}

export function EvidenceSideNote({ source, sourceId, page }: EvidenceSideNoteProps) {
  if (!sourceId) {
    return null;
  }

  return (
    <div className="rounded-md border border-border/70 bg-muted/20 px-3 py-2 text-xs">
      <div className="font-semibold text-foreground/90">Evidence Side Note</div>
      <div className="mt-1 text-muted-foreground">source: {source}</div>
      <div className="text-muted-foreground">chunk: {sourceId}</div>
      <div className="text-muted-foreground">page: {page}</div>
    </div>
  );
}
