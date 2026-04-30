type TelemetryEventName =
  | 'ui_event'
  | 'stream_event'
  | 'import_event'
  | 'search_event'
  | 'workflow_event';

type TelemetryPayload = Record<string, unknown>;
type LegacyTelemetryPayload = TelemetryPayload & { event?: string; eventName?: string };

export interface WorkflowTelemetryPayload extends TelemetryPayload {
  event: string;
  page?: 'chat' | 'search' | 'knowledge-base' | 'read' | 'analytics';
  scopeType?: 'global' | 'knowledge-base' | 'paper';
  scopeId?: string | null;
  sessionId?: string | null;
  messageId?: string | null;
  runId?: string | null;
  traceId?: string | null;
  retrievalTraceId?: string | null;
  status?: string;
  phase?: string;
  stage?: string;
  durationMs?: number | null;
  tokensUsed?: number;
  cost?: number;
  errorCode?: string;
  errorMessage?: string;
}

const sinks = {
  console: (event: TelemetryEventName, payload: TelemetryPayload) => {
    if (typeof window === 'undefined') {
      return;
    }
    console.debug('[telemetry]', event, payload);
  },
};

function emit(event: TelemetryEventName, payload: TelemetryPayload) {
  Object.values(sinks).forEach((sink) => sink(event, payload));
}

function normalizeTelemetryArgs(eventNameOrPayload: string | LegacyTelemetryPayload, payload: TelemetryPayload = {}) {
  if (typeof eventNameOrPayload === 'string') {
    return { eventName: eventNameOrPayload, ...payload, timestamp: Date.now() };
  }

  return { ...eventNameOrPayload, timestamp: Date.now() };
}

export function trackUIEvent(eventNameOrPayload: string | LegacyTelemetryPayload, payload: TelemetryPayload = {}) {
  emit('ui_event', normalizeTelemetryArgs(eventNameOrPayload, payload));
}

export function trackStreamEvent(eventNameOrPayload: string | LegacyTelemetryPayload, payload: TelemetryPayload = {}) {
  emit('stream_event', normalizeTelemetryArgs(eventNameOrPayload, payload));
}

export function trackImportEvent(eventNameOrPayload: string | LegacyTelemetryPayload, payload: TelemetryPayload = {}) {
  emit('import_event', normalizeTelemetryArgs(eventNameOrPayload, payload));
}

export function trackSearchEvent(eventNameOrPayload: string | LegacyTelemetryPayload, payload: TelemetryPayload = {}) {
  emit('search_event', normalizeTelemetryArgs(eventNameOrPayload, payload));
}

export function trackWorkflowEvent(payload: WorkflowTelemetryPayload) {
  emit('workflow_event', { ...payload, timestamp: Date.now() });
}
