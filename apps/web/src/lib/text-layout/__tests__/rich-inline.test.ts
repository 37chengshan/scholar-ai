import { describe, expect, it } from 'vitest';
import { tokenizeRichInline } from '@/lib/text-layout/rich-inline';

describe('tokenizeRichInline', () => {
  it('extracts citation tokens', () => {
    const tokens = tokenizeRichInline('claim [1] and [2]');
    const citationCount = tokens.filter((token) => token.kind === 'citation').length;
    expect(citationCount).toBe(2);
  });
});
