import { describe, expect, it } from 'vitest';
import { measureText } from '@/lib/text-layout/measure';
import { DEFAULT_TEXT_FONT } from '@/lib/text-layout/font';

describe('measureText', () => {
  it('returns positive line and height', () => {
    const result = measureText({
      text: 'ScholarAI evidence layout runtime test',
      width: 180,
      font: DEFAULT_TEXT_FONT,
    });

    expect(result.lineCount).toBeGreaterThan(0);
    expect(result.height).toBeGreaterThan(0);
  });
});
