import { describe, expect, it } from 'vitest';
import { measureText } from '@/lib/text-layout/measure';
import { DEFAULT_TEXT_FONT } from '@/lib/text-layout/font';
import { textMeasureCache } from '@/lib/text-layout/cache';

describe('text layout performance', () => {
  it('reuses cached measurements faster than cold measurements', () => {
    textMeasureCache.clear();

    const inputs = Array.from({ length: 200 }, (_, i) => ({
      text: `message-${i} evidence quality and citation rendering`,
      width: 560,
      font: DEFAULT_TEXT_FONT,
    }));

    const coldStart = performance.now();
    for (const input of inputs) {
      measureText({
        text: input.text,
        width: input.width,
        font: input.font,
      });
    }
    const coldElapsed = performance.now() - coldStart;

    const warmStart = performance.now();
    for (const input of inputs) {
      measureText({
        text: input.text,
        width: input.width,
        font: input.font,
      });
    }
    const warmElapsed = performance.now() - warmStart;

    expect(warmElapsed).toBeLessThan(coldElapsed);
    expect(textMeasureCache.size()).toBeGreaterThan(0);
  });
});
