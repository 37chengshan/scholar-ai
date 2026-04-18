import { describe, expect, it } from 'vitest';

import { normalizeSSEEventEnvelope } from './sseEventAdapter';

describe('normalizeSSEEventEnvelope', () => {
  it('accepts canonical reasoning events', () => {
    const normalized = normalizeSSEEventEnvelope({
      message_id: 'm1',
      event_type: 'reasoning',
      data: { delta: 'thinking...' },
    });

    expect(normalized).not.toBeNull();
    expect(normalized?.event_type).toBe('reasoning');
  });

  it('accepts canonical phase events', () => {
    const normalized = normalizeSSEEventEnvelope({
      message_id: 'm1',
      event_type: 'phase',
      data: { phase: 'retrieving', label: 'retrieving docs' },
    });

    expect(normalized).not.toBeNull();
    expect(normalized?.event_type).toBe('phase');
    expect(normalized?.data.phase).toBe('retrieving');
  });

  it('returns null for legacy and unsupported events', () => {
    const normalized = normalizeSSEEventEnvelope({
      message_id: 'm1',
      event_type: 'thought',
      data: {},
    });

    expect(normalized).toBeNull();
  });
});
