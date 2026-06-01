/**
 * PDF Blob URL Cache
 *
 * Module-level cache that deduplicates PDF blob fetches.
 * Multiple components (PDFViewer, ThumbnailStrip) sharing the same
 * paper ID will reuse a single fetch + createObjectURL result.
 */

import * as papersApi from '@/services/papersApi';

const blobUrlCache = new Map<string, Promise<string>>();

/**
 * Get or create a blob URL for a paper's PDF.
 * Deduplicates concurrent requests for the same paper ID.
 */
export async function getOrCreateBlobUrl(
  paperId: string,
): Promise<string> {
  const existing = blobUrlCache.get(paperId);
  if (existing) {
    return existing;
  }

  const promise = papersApi.downloadPdfBlob(paperId).then((blob) => {
    return URL.createObjectURL(blob);
  });

  blobUrlCache.set(paperId, promise);

  // If the fetch fails, remove from cache so retries are possible
  promise.catch(() => {
    blobUrlCache.delete(paperId);
  });

  return promise;
}

/**
 * Revoke and remove a specific paper's blob URL from cache.
 */
export function revokeBlobUrl(paperId: string): void {
  const cached = blobUrlCache.get(paperId);
  if (!cached) {
    return;
  }

  cached
    .then((url) => {
      URL.revokeObjectURL(url);
    })
    .catch(() => {
      // ignore — fetch already failed
    });

  blobUrlCache.delete(paperId);
}

/**
 * Revoke all cached blob URLs. Call on app teardown if needed.
 */
export function revokeAllBlobUrls(): void {
  for (const [paperId] of blobUrlCache) {
    revokeBlobUrl(paperId);
  }
}
