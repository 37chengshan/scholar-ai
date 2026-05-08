import { describe, expect, it } from 'vitest';
import { buildChatHref } from './chatHandoff';

describe('chatHandoff session isolation', () => {
  it('keeps scoped chat href free of session identifiers before handoff decoration', () => {
    expect(buildChatHref({ paperId: 'paper-1' })).toBe('/chat?paperId=paper-1');
    expect(buildChatHref({ kbId: 'kb-1' })).toBe('/chat?kbId=kb-1');
  });
});
