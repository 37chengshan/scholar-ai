import { useMemo } from 'react';

export function useChunkHighlight(sourceId: string) {
  return useMemo(() => ({
    highlightedSourceChunkId: sourceId,
    hasHighlight: Boolean(sourceId),
  }), [sourceId]);
}
