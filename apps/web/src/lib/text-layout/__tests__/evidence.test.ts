import { describe, expect, it } from 'vitest';
import { measureEvidenceBlock } from '@/lib/text-layout/evidence';
import { tokenizeEvidenceInline } from '@/lib/text-layout/rich-inline';

describe('evidence text layout helpers', () => {
  it('measures evidence block height', () => {
    const measured = measureEvidenceBlock(
      {
        paper_id: 'paper-1',
        section_path: 'methods',
        text: 'This is a structured evidence block for testing.',
      },
      320,
    );

    expect(measured.height).toBeGreaterThan(0);
    expect(measured.lineCount).toBeGreaterThan(0);
  });

  it('tokenizes evidence metadata into inline tokens', () => {
    const tokens = tokenizeEvidenceInline({
      paperId: 'paper-1',
      pageNum: 3,
      sectionPath: 'results',
    });

    expect(tokens[0]?.text).toBe('paper-1');
    expect(tokens.some((token) => token.text.includes('results'))).toBe(true);
  });
});
