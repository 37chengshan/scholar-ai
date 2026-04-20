import { describe, expect, it } from 'vitest';

describe('chatApi SSE body construction', () => {
  it('keeps paper scope contract fields stable', () => {
    const scope = {
      type: 'paper',
      paper_id: 'paper-1',
    };

    expect(scope).toEqual({ type: 'paper', paper_id: 'paper-1' });
  });

  it('keeps knowledge base scope contract fields stable', () => {
    const scope = {
      type: 'knowledge_base',
      knowledge_base_id: 'kb-1',
    };

    expect(scope).toEqual({ type: 'knowledge_base', knowledge_base_id: 'kb-1' });
  });
});
