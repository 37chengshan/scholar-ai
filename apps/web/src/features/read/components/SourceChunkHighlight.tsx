interface SourceChunkHighlightProps {
  sourceChunkId: string;
}

export function SourceChunkHighlight({ sourceChunkId }: SourceChunkHighlightProps) {
  if (!sourceChunkId) {
    return null;
  }

  return (
    <div className="mb-2 rounded-md border border-primary/40 bg-primary/10 px-3 py-2 text-xs text-primary">
      source highlight: {sourceChunkId}
    </div>
  );
}
