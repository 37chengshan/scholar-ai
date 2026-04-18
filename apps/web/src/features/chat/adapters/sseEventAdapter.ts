
export type CanonicalSSEEventType =
  | 'session_start'
  | 'routing_decision'
  | 'phase'
  | 'reasoning'
  | 'message'
  | 'tool_call'
  | 'tool_result'
  | 'citation'
  | 'confirmation_required'
  | 'done'
  | 'heartbeat'
  | 'error';

export interface RawSSEEventEnvelope {
  message_id: string;
  event_type: string;
  data: unknown;
  sequence?: number;
  timestamp?: number;
}

export interface CanonicalSSEEventEnvelope {
  message_id: string;
  event_type: CanonicalSSEEventType;
  data: Record<string, unknown>;
  sequence?: number;
  timestamp?: number;
}

function ensureObjectData(data: unknown): Record<string, unknown> {
  if (typeof data === 'object' && data !== null) {
    return data as Record<string, unknown>;
  }
  return { content: data };
}

export function normalizeSSEEventEnvelope(
  envelope: RawSSEEventEnvelope
): CanonicalSSEEventEnvelope | null {
  const data = ensureObjectData(envelope.data);

  switch (envelope.event_type) {
    case 'session_start':
    case 'routing_decision':
    case 'phase':
    case 'reasoning':
    case 'message':
    case 'tool_call':
    case 'tool_result':
    case 'citation':
    case 'confirmation_required':
    case 'done':
    case 'heartbeat':
    case 'error':
      return {
        ...envelope,
        data,
        event_type: envelope.event_type,
      };

    default:
      return null;
  }
}
