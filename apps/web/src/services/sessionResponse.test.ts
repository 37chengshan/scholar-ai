import { describe, expect, it } from 'vitest';
import { extractSessionMessages } from './sessionResponse';

describe('extractSessionMessages', () => {
  it('reads nested data.messages', () => {
    const messages = extractSessionMessages({
      data: {
        messages: [{ id: 'm1' }],
      },
    });

    expect(messages).toEqual([{ id: 'm1' }]);
  });

  it('falls back to top-level messages', () => {
    const messages = extractSessionMessages({
      messages: [{ id: 'm2' }],
    });

    expect(messages).toEqual([{ id: 'm2' }]);
  });

  it('returns an empty array when absent', () => {
    expect(extractSessionMessages({})).toEqual([]);
  });
});