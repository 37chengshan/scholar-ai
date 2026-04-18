import { describe, expect, it } from 'vitest';

import { normalizeSSEEventEnvelope } from './sseEventAdapter';

describe('normalizeSSEEventEnvelope', () => {
  it('maps thought to reasoning', () => {
    const normalized = normalizeSSEEventEnvelope({
      message_id: 'm1',
      event_type: 'thought',
      data: { delta: 'thinking...' },
    });

    expect(normalized).not.toBeNull();
    expect(normalized?.event_type).toBe('reasoning');
    expect(normalized?.legacy_event_type).toBe('thought');
  });

  it('maps phase_change to phase', () => {
    const normalized = normalizeSSEEventEnvelope({
      message_id: 'm1',
      event_type: 'phase_change',
      data: { phase: 'retrieving', label: 'retrieving docs' },
    });

    expect(normalized).not.toBeNull();
    expect(normalized?.event_type).toBe('phase');
    expect(normalized?.legacy_event_type).toBe('phase_change');
    expect(normalized?.data.phase).toBe('retrieving');
  });

  it('normalizes thinking_status to phase payload', () => {
    const normalized = normalizeSSEEventEnvelope({
      message_id: 'm1',
      event_type: 'thinking_status',
      data: { status: 'verifying' },
    });

    expect(normalized).not.toBeNull();
    expect(normalized?.event_type).toBe('phase');
    expect(normalized?.data.phase).toBe('verifying');
    expect(normalized?.data.label).toBe('verifying');
  });

  it('returns null for unsupported events', () => {
    const normalized = normalizeSSEEventEnvelope({
      message_id: 'm1',
      event_type: 'unknown_legacy_event',
      data: {},
    });

    expect(normalized).toBeNull();
  });
});
