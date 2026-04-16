/**
 * SSE Parser Utility
 *
 * Parses Server-Sent Events (SSE) streams with:
 * - Standard SSE format parsing (id/event/data)
 * - Contract validation for event fields
 * - Last-Event-ID support for resumption
 * - EventSource integration helpers
 * - message_id extraction (HARD RULE 0.2)
 *
 * Standard SSE Format:
 * ```
 * id: <uuid>
 * event: <type>
 * data: <json with message_id>
 *
 * ```
 */

import { SSEEventType, SSEEvent } from '../services/sseService';

/**
 * Contract violation error
 */
export class ContractViolationError extends Error {
  constructor(
    public readonly eventType: string,
    public readonly missingFields: string[],
    public readonly payload: Record<string, unknown>
  ) {
    super(
      `Contract violation for event '${eventType}': missing required fields [${missingFields.join(', ')}]`
    );
    this.name = 'ContractViolationError';
  }
}

/**
 * Parsed SSE event structure
 * Includes message_id for event correlation (HARD RULE 0.2)
 */
export interface ParsedSSEEvent {
  id?: string;
  type: SSEEventType;
  data: Record<string, unknown>;
  /** Message ID for event correlation (HARD RULE 0.2) */
  message_id?: string;
  raw: string;
}

/**
 * Event contract definitions - required fields per event type
 *
 * HARD RULE 0.2: message_id is required for all non-heartbeat events.
 * P2: Contract Validation
 * Each event type has specific required fields that must be present.
 * This enforces the frontend-backend contract.
 *
 * Note: Uses string keys to support both new and legacy event types.
 */
export const EVENT_CONTRACTS: Record<string, string[]> = {
  // Session initialization (HARD RULE 0.2)
  session_start: ['session_id', 'task_type', 'message_id'],

  // Routing decision
  routing_decision: ['route', 'confidence', 'message_id'],

  // Phase switching
  phase: ['phase', 'label', 'message_id'],

  // Reasoning stream
  reasoning: ['delta', 'seq', 'message_id'],

  // Message stream
  message: ['delta', 'seq', 'message_id'],

  // Tool execution events
  tool_call: ['id', 'tool', 'label', 'status', 'message_id'],
  tool_result: ['id', 'tool', 'label', 'status', 'message_id'],

  // Citation events
  citation: ['paper_id', 'title', 'message_id'],

  // User confirmation events
  confirmation_required: ['operation', 'risk_level', 'message_id'],

  // Cancel events
  cancel: ['reason', 'message_id'],

  // Stream completion
  done: ['finish_reason', 'message_id'],

  // Error events
  error: ['code', 'message', 'message_id'],

  // Heartbeat - no required fields (keepalive)
  heartbeat: [],

  // Legacy events (deprecated - kept for backward compatibility)
  thought: ['content', 'timestamp'],
  thinking_status: ['status', 'summary', 'sequence', 'timestamp', 'session_id'],
};

/**
 * Parse a single SSE event from text
 *
 * Handles standard SSE format:
 * - id: <uuid> (optional)
 * - event: <type>
 * - data: <json with message_id>
 *
 * HARD RULE 0.2: Extracts message_id from data payload.
 *
 * @param sseText - Raw SSE text (single event)
 * @returns Parsed event or null if invalid
 */
export function parseSSELine(sseText: string): ParsedSSEEvent | null {
  if (!sseText || sseText.trim() === '') {
    return null;
  }

  const lines = sseText.split('\n');
  let id: string | undefined;
  let eventType: SSEEventType | undefined;
  let dataStr: string | undefined;

  for (const line of lines) {
    const trimmedLine = line.trim();

    if (trimmedLine.startsWith('id:')) {
      id = trimmedLine.slice(3).trim();
    } else if (trimmedLine.startsWith('event:')) {
      eventType = trimmedLine.slice(6).trim() as SSEEventType;
    } else if (trimmedLine.startsWith('data:')) {
      // Handle multi-line data (concatenate)
      const dataPart = trimmedLine.slice(5).trim();
      dataStr = dataStr ? `${dataStr}${dataPart}` : dataPart;
    }
    // Empty lines separate events - handled by caller
  }

  // Validate required fields
  if (!eventType) {
    return null;
  }

  // Parse JSON data
  let data: Record<string, unknown> = {};
  if (dataStr) {
    try {
      data = JSON.parse(dataStr);
    } catch {
      // Invalid JSON - return null
      return null;
    }
  }

  // Extract message_id (HARD RULE 0.2)
  const messageId = data.message_id as string | undefined;
  if (!messageId && eventType !== 'heartbeat') {
    console.warn('[SSE Parser] Event missing message_id:', eventType);
  }

  return {
    id,
    type: eventType,
    data,
    message_id: messageId,
    raw: sseText,
  };
}

/**
 * Parse multiple SSE events from stream text
 *
 * Handles multiple events separated by double newlines.
 *
 * @param streamText - Raw SSE stream text (multiple events)
 * @returns Array of parsed events
 */
export function parseSSEStream(streamText: string): ParsedSSEEvent[] {
  if (!streamText) {
    return [];
  }

  // Split by double newline (event separator)
  const events = streamText.split('\n\n');
  const results: ParsedSSEEvent[] = [];

  for (const eventText of events) {
    const parsed = parseSSELine(eventText);
    if (parsed) {
      results.push(parsed);
    }
  }

  return results;
}

/**
 * Validate event against contract
 *
 * P2: Contract Validation
 * Ensures event payload contains all required fields for its type.
 *
 * @param event - Parsed SSE event
 * @param expectedType - Optional expected event type to validate
 * @returns true if valid, throws ContractViolationError if invalid
 */
export function validateEventContract(
  event: ParsedSSEEvent,
  expectedType?: SSEEventType
): boolean {
  // Validate event type matches expected (if provided)
  if (expectedType && event.type !== expectedType) {
    throw new ContractViolationError(
      event.type,
      [`expected type '${expectedType}'`],
      event.data
    );
  }

  // Get required fields for this event type
  const requiredFields = EVENT_CONTRACTS[event.type];

  // Some events have no contract requirements (e.g., heartbeat)
  if (!requiredFields || requiredFields.length === 0) {
    return true;
  }

  // Check for missing fields
  const missingFields = requiredFields.filter(
    (field) => !(field in event.data) || event.data[field] === undefined
  );

  if (missingFields.length > 0) {
    throw new ContractViolationError(
      event.type,
      missingFields,
      event.data
    );
  }

  return true;
}

/**
 * SSE Parser configuration
 */
export interface SSEParserConfig {
  /** Called when a valid event is parsed */
  onEvent: (event: ParsedSSEEvent) => void;
  /** Called when an error occurs */
  onError: (error: Error) => void;
  /** Called when contract validation fails */
  onContractViolation?: (error: ContractViolationError) => void;
  /** Whether to validate contracts (default: true) */
  validateContracts?: boolean;
}

/**
 * Create an SSE parser for EventSource integration
 *
 * Provides a parser that can be used with fetch streams or EventSource.
 * Handles incremental parsing with buffer management.
 *
 * @param config - Parser configuration
 * @returns Parser functions
 */
export function createSSEParser(config: SSEParserConfig) {
  const { onEvent, onError, onContractViolation, validateContracts = true } = config;
  let buffer = '';

  /**
   * Process incoming chunk of SSE data
   */
  function processChunk(chunk: string): void {
    buffer += chunk;

    // Split by double newline (event separator)
    const parts = buffer.split('\n\n');

    // Keep the last incomplete part in buffer
    buffer = parts.pop() || '';

    // Process complete events
    for (const eventText of parts) {
      const event = parseSSELine(eventText);
      if (event) {
        // Validate contract if enabled
        if (validateContracts) {
          try {
            validateEventContract(event);
            onEvent(event);
          } catch (error) {
            if (error instanceof ContractViolationError) {
              if (onContractViolation) {
                onContractViolation(error);
              } else {
                onError(error);
              }
            } else {
              onError(error as Error);
            }
          }
        } else {
          onEvent(event);
        }
      }
    }
  }

  /**
   * Process any remaining data in buffer
   */
  function flush(): void {
    if (buffer.trim()) {
      const event = parseSSELine(buffer);
      if (event) {
        if (validateContracts) {
          try {
            validateEventContract(event);
            onEvent(event);
          } catch (error) {
            if (error instanceof ContractViolationError) {
              if (onContractViolation) {
                onContractViolation(error);
              } else {
                onError(error);
              }
            } else {
              onError(error as Error);
            }
          }
        } else {
          onEvent(event);
        }
      }
    }
    buffer = '';
  }

  /**
   * Reset parser state
   */
  function reset(): void {
    buffer = '';
  }

  return {
    processChunk,
    flush,
    reset,
  };
}

/**
 * Convert parsed event to SSEEvent format (for compatibility with existing code)
 * Includes message_id for event correlation (HARD RULE 0.2)
 */
export function toSSEEvent(parsed: ParsedSSEEvent): SSEEvent {
  return {
    type: parsed.type,
    content: parsed.data,
    timestamp: parsed.data.timestamp as string | undefined,
    tool: parsed.data.tool as string | undefined,
    result: parsed.data.result,
    event: parsed.type,
    data: parsed.data,
    message_id: parsed.message_id,
  };
}

/**
 * Last-Event-ID tracking for resumption
 */
export class LastEventIdTracker {
  private lastEventId: string | null = null;

  /**
   * Update last event ID from parsed event
   */
  update(event: ParsedSSEEvent): void {
    if (event.id) {
      this.lastEventId = event.id;
    }
  }

  /**
   * Get current last event ID
   */
  get(): string | null {
    return this.lastEventId;
  }

  /**
   * Get headers for resumption request
   */
  getHeaders(): Record<string, string> {
    if (this.lastEventId) {
      return { 'Last-Event-ID': this.lastEventId };
    }
    return {};
  }

  /**
   * Clear stored event ID
   */
  clear(): void {
    this.lastEventId = null;
  }
}