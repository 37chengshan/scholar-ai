import { describe, expect, it, vi } from 'vitest';
import { buildChatHref, navigateToChatWithHandoff } from './chatHandoff';

describe('chatHandoff', () => {
  it('builds durable compare scope into the chat URL', () => {
    expect(buildChatHref({ paperIds: ['paper-1', 'paper-2'] })).toBe('/chat?paper_ids=paper-1%2Cpaper-2');
    expect(buildChatHref({ kbId: 'kb-1', paperId: 'paper-1' })).toBe('/chat?paperId=paper-1&kbId=kb-1');
  });

  it('passes one-shot handoff state through router navigation', () => {
    const navigate = vi.fn();

    navigateToChatWithHandoff(
      navigate as any,
      { kbId: 'kb-1' },
      {
        origin: 'review',
        promptDraft: 'Check the weakly supported claim.',
        evidence: [{ paperId: 'paper-1', claim: 'Weak claim' }],
        returnTo: '/knowledge-bases/kb-1?tab=review&runId=run-1',
      },
    );

    expect(navigate).toHaveBeenCalledWith('/chat?kbId=kb-1', {
      state: {
        handoff: {
          origin: 'review',
          promptDraft: 'Check the weakly supported claim.',
          evidence: [{ paperId: 'paper-1', claim: 'Weak claim' }],
          returnTo: '/knowledge-bases/kb-1?tab=review&runId=run-1',
        },
      },
    });
  });
});
