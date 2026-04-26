import { describe, expect, it } from 'vitest';
import { LruCache } from '@/lib/text-layout/cache';

describe('LruCache', () => {
  it('evicts oldest entry', () => {
    const cache = new LruCache<string, number>(2);
    cache.set('a', 1);
    cache.set('b', 2);
    cache.set('c', 3);

    expect(cache.get('a')).toBeUndefined();
    expect(cache.get('b')).toBe(2);
    expect(cache.get('c')).toBe(3);
  });
});
