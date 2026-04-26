import { describe, expect, it } from 'vitest';
import { measureText } from '@/lib/text-layout/measure';
import { DEFAULT_TEXT_FONT } from '@/lib/text-layout/font';

describe('text layout performance', () => {
  it('measures 1000 messages quickly', () => {
    const start = performance.now();
    for (let i = 0; i < 1000; i += 1) {
      measureText({
        text: `message-${i} evidence quality and citation rendering`,
        width: 560,
        font: DEFAULT_TEXT_FONT,
      });
    }
    const elapsed = performance.now() - start;
    expect(elapsed).toBeLessThan(200);
  });
});
