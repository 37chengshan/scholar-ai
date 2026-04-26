export interface OcclusionWindow {
  startIndex: number;
  endIndex: number;
}

export function computeOcclusionWindow(scrollTop: number, viewportHeight: number, estimatedItemHeight: number, totalItems: number, overscan = 4): OcclusionWindow {
  const safeHeight = Math.max(1, estimatedItemHeight);
  const startIndex = Math.max(0, Math.floor(scrollTop / safeHeight) - overscan);
  const visibleCount = Math.ceil(viewportHeight / safeHeight) + overscan * 2;
  const endIndex = Math.min(totalItems, startIndex + visibleCount);
  return { startIndex, endIndex };
}
