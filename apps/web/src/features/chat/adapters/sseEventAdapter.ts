import type { AgentPhase } from '@/types/chat';

const phaseAliases: Record<string, AgentPhase> = {
  idle: 'idle',
  thinking: 'analyzing',
  analyzing: 'analyzing',
  retrieve: 'retrieving',
  retrieving: 'retrieving',
  reading: 'reading',
  tool_calling: 'tool_calling',
  synthesizing: 'synthesizing',
  verify: 'verifying',
  verifying: 'verifying',
  done: 'done',
  error: 'error',
  cancelled: 'cancelled',
};

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
  legacy_event_type?: string;
}

function ensureObjectData(data: unknown): Record<string, unknown> {
  if (typeof data === 'object' && data !== null) {
    return data as Record<string, unknown>;
  }
  return { content: data };
}

function normalizeLegacyPhase(data: Record<string, unknown>): Record<string, unknown> {
  const statusLike =
    (data.phase as string) ||
    (data.status as string) ||
    (data.step as string) ||
    'analyzing';

  const phase = phaseAliases[statusLike.toLowerCase()] ?? 'analyzing';
  const label =
    (data.label as string) ||
    (data.status_text as string) ||
    (data.step as string) ||
    String(statusLike);

  return {
    ...data,
    phase,
    label,
  };
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

    case 'phase_change':
      return {
        ...envelope,
        data,
        event_type: 'phase',
        legacy_event_type: 'phase_change',
      };

    case 'thought':
      return {
        ...envelope,
        data,
        event_type: 'reasoning',
        legacy_event_type: 'thought',
      };

    case 'thinking_status':
    case 'step_progress':
      return {
        ...envelope,
        data: normalizeLegacyPhase(data),
        event_type: 'phase',
        legacy_event_type: envelope.event_type,
      };

    default:
      return null;
  }
}
