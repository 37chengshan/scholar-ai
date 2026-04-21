
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
  | 'cancel'
  | 'done'
  | 'heartbeat'
  | 'error'
  // Run protocol events
  | 'run_start'
  | 'run_phase_change'
  | 'step_start'
  | 'step_complete'
  | 'run_complete'
  | 'recovery_available'
  | 'evidence'
  | 'artifact';

export interface RawSSEEventEnvelope {
  message_id: string;
  event_type?: string;
  event?: string;
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
  const normalizedEventType = envelope.event_type ?? envelope.event;
  if (!normalizedEventType) {
    return null;
  }

  const data = ensureObjectData(envelope.data);
  const maybeWrappedData =
    typeof data.event === 'string' &&
    Object.prototype.hasOwnProperty.call(data, 'data')
      ? ensureObjectData(data.data)
      : data;

  switch (normalizedEventType) {
    case 'session_start':
    case 'routing_decision':
    case 'phase':
    case 'reasoning':
    case 'message':
    case 'tool_call':
    case 'tool_result':
    case 'citation':
    case 'confirmation_required':
    case 'cancel':
    case 'done':
    case 'heartbeat':
    case 'error':
    // Run protocol events
    case 'run_start':
    case 'run_phase_change':
    case 'step_start':
    case 'step_complete':
    case 'run_complete':
    case 'recovery_available':
    case 'evidence':
    case 'artifact':
      return {
        message_id: envelope.message_id,
        data: maybeWrappedData,
        event_type: normalizedEventType,
        sequence: envelope.sequence,
        timestamp: envelope.timestamp,
      };

    default:
      return null;
  }
}
