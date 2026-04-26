import { describe, expect, it } from 'vitest';
import { computeBubbleShrinkwrap } from '@/lib/text-layout/shrinkwrap';
import { DEFAULT_TEXT_FONT } from '@/lib/text-layout/font';

describe('computeBubbleShrinkwrap', () => {
  it('caps width by maxWidth and keeps minimum width', () => {
    const result = computeBubbleShrinkwrap('hello world', 240, DEFAULT_TEXT_FONT);
    expect(result.width).toBeLessThanOrEqual(240);
    expect(result.width).toBeGreaterThanOrEqual(140);
    expect(result.height).toBeGreaterThan(0);
  });
});
