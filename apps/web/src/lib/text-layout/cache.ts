export class LruCache<K, V> {
  private readonly maxSize: number;
  private readonly store = new Map<K, V>();

  constructor(maxSize = 400) {
    this.maxSize = Math.max(1, maxSize);
  }

  get(key: K): V | undefined {
    if (!this.store.has(key)) {
      return undefined;
    }
    const value = this.store.get(key) as V;
    this.store.delete(key);
    this.store.set(key, value);
    return value;
  }

  set(key: K, value: V): void {
    if (this.store.has(key)) {
      this.store.delete(key);
    }
    this.store.set(key, value);
    if (this.store.size <= this.maxSize) {
      return;
    }
    const oldest = this.store.keys().next().value;
    if (oldest !== undefined) {
      this.store.delete(oldest);
    }
  }

  clear(): void {
    this.store.clear();
  }

  size(): number {
    return this.store.size;
  }
}

export const textMeasureCache = new LruCache<string, { height: number; lineCount: number; maxLineWidth: number }>(800);
