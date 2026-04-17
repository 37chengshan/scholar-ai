export type TelemetryEventName =
  | 'ui_event'
  | 'stream_event'
  | 'import_event'
  | 'search_event';

export interface TelemetryPayload {
  event: string;
  timestamp?: number;
  [key: string]: unknown;
}

function emit(eventName: TelemetryEventName, payload: TelemetryPayload): void {
  const event = {
    ...payload,
    timestamp: payload.timestamp ?? Date.now(),
  };

  // V1: local sink only; can be wired to backend endpoint later.
  if (import.meta.env.DEV) {
    // eslint-disable-next-line no-console
    console.debug(`[telemetry:${eventName}]`, event);
  }
}

export function trackUIEvent(payload: TelemetryPayload): void {
  emit('ui_event', payload);
}

export function trackStreamEvent(payload: TelemetryPayload): void {
  emit('stream_event', payload);
}

export function trackImportEvent(payload: TelemetryPayload): void {
  emit('import_event', payload);
}

export function trackSearchEvent(payload: TelemetryPayload): void {
  emit('search_event', payload);
}
