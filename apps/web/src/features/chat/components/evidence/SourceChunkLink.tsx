interface SourceChunkLinkProps {
  sourceChunkId: string;
  onOpen: (sourceChunkId: string) => void;
}

export function SourceChunkLink({ sourceChunkId, onOpen }: SourceChunkLinkProps) {
  return (
    <button
      type="button"
      onClick={() => onOpen(sourceChunkId)}
      className="text-[11px] font-medium text-primary underline-offset-2 hover:underline"
    >
      {sourceChunkId}
    </button>
  );
}
