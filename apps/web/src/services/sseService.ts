/**
 * SSE Service with Auto-Reconnect
 *
 * Manages Server-Sent Events connections with:
 * - POST-based streaming (fetch API)
 * - Automatic reconnection with exponential backoff (3 retries)
 * - Heartbeat monitoring (60s timeout)
 * - Last-Event-ID support for resumption
 * - Proper cleanup on disconnect
 * - message_id binding (HARD RULE 0.2)
 *
 * Event types from backend:
 * - session_start: Session initialization with message_id binding
 * - routing_decision: Agent routing decision (complexity analysis)
 * - phase: Agent phase switching
 * - reasoning: Thinking content stream
 * - message: Final response content stream
 * - tool_call: Agent invoking tool
 * - tool_result: Tool execution result
 * - citation: Citation information
 * - confirmation_required: Dangerous operation needs approval
 * - cancel: User cancellation
 * - done: Stream complete
 * - heartbeat: 15s keepalive
 * - error: Error notification
 */

import { AgentPhase } from '@/types/chat';
export type {
  StreamEventEnvelope as SharedStreamEventEnvelope,
  StreamEventType as SharedStreamEventType,
  SessionStartEventData as SharedSessionStartEventData,
  RoutingDecisionEventData as SharedRoutingDecisionEventData,
  ReasoningEventData as SharedReasoningEventData,
  MessageEventData as SharedMessageEventData,
  ToolCallEventData as SharedToolCallEventData,
  ToolResultEventData as SharedToolResultEventData,
  DoneEventData as SharedDoneEventData,
  ErrorEventData as SharedErrorEventData,
} from '@scholar-ai/types';

/**
 * SSE Event Types (from backend Agent-Native architecture)
 * These come from the 'event:' line in SSE stream
 *
 * HARD RULE 0.2: All events must carry message_id
 * The message_id binds all events in a single AI response stream.
 */
export type SSEEventType =
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
  | 'error';

/**
 * SSEEventEnvelope - Standard envelope for all SSE events
 *
 * HARD RULE 0.2: message_id is mandatory for all events.
 * All events in a single AI response stream share the same message_id.
 * This enables frontend to correlate events with the originating user message.
 */
export interface SSEEventEnvelope<T = unknown> {
  /** Event type from 'event:' line - authoritative source */
  event: SSEEventType;
  /** Event-specific payload */
  data: T;
  /** Message ID - binds all events in this AI response stream (REQUIRED) */
  message_id: string;
}

/**
 * Session Start Event Data
 * First event in stream, establishes message_id binding
 */
export interface SessionStartEventData {
  session_id: string;
  task_type: 'single_paper' | 'kb_qa' | 'compare' | 'general';
  message_id: string;
}

/**
 * Routing Decision Event Data
 * Determines query processing path
 */
export interface RoutingDecisionEventData {
  // Backend may send 'route' (old) or 'decision' (Sprint 3 fast path)
  route?: 'rag' | 'knowledge_graph' | 'hybrid' | 'external_search' | 'clarification';
  decision?: 'simple' | 'complex' | 'agent';
  confidence: number;
  reason: string;
  estimated_steps?: number;
  alternatives?: Array<{
    route: string;
    confidence: number;
  }>;
}

/**
 * Phase Event Data
 * Indicates current agent processing phase
 */
export interface PhaseEventData {
  phase: AgentPhase;
  label: string;
}

/**
 * Reasoning Event Data (streaming)
 * AI thinking content - incremental deltas
 */
export interface ReasoningEventData {
  delta: string;
  seq: number;
}

/**
 * Message Event Data (streaming)
 * Final response content - incremental deltas
 */
export interface MessageEventData {
  delta: string;
  seq: number;
}

/**
 * Tool Call Event Data
 * Agent invoking a tool
 */
export interface ToolCallEventData {
  id: string;
  tool: string;
  label: string;
  status: 'running';
}

/**
 * Tool Result Event Data
 * Tool execution result
 */
export interface ToolResultEventData {
  id: string;
  tool: string;
  label: string;
  status: 'success' | 'failed';
  summary?: string;
}

/**
 * Citation Event Data
 * Reference to source paper
 */
export interface CitationEventData {
  paper_id: string;
  title: string;
  pages: number[];
  hits: number;
}

/**
 * Confirmation Required Event Data
 * Dangerous operation needs user approval
 */
export interface ConfirmationRequiredEventData {
  operation: string;
  risk_level: 'low' | 'medium' | 'high';
  details: string;
}

/**
 * Cancel Event Data
 * User cancelled the stream
 */
export interface CancelEventData {
  reason: 'user_stop' | 'timeout' | 'network_error';
}

/**
 * Done Event Data
 * Stream completion marker
 */
export interface DoneEventData {
  finish_reason: 'stop' | 'tool_calls' | 'length' | 'cancel';
  tokens_used?: number;
  cost?: number;
  total_time_ms?: number;
  answer_mode?: 'full' | 'partial' | 'abstain';
  claims?: unknown[];
  citations?: unknown[];
  evidence_blocks?: unknown[];
  quality?: Record<string, unknown>;
  retrieval_trace_id?: string;
  error_state?: string | null;
  trace?: Record<string, unknown>;
}

/**
 * Error Event Data
 * Error notification
 */
export interface ErrorEventData {
  code: string;
  message: string;
  recoverable: boolean;
}

/**
 * Typed SSE Event Envelope variants
 */
export type SessionStartEvent = SSEEventEnvelope<SessionStartEventData>;
export type RoutingDecisionEvent = SSEEventEnvelope<RoutingDecisionEventData>;
export type PhaseEvent = SSEEventEnvelope<PhaseEventData>;
export type ReasoningEvent = SSEEventEnvelope<ReasoningEventData>;
export type MessageEvent = SSEEventEnvelope<MessageEventData>;
export type ToolCallEvent = SSEEventEnvelope<ToolCallEventData>;
export type ToolResultEvent = SSEEventEnvelope<ToolResultEventData>;
export type CitationEvent = SSEEventEnvelope<CitationEventData>;
export type ConfirmationRequiredEvent = SSEEventEnvelope<ConfirmationRequiredEventData>;
export type CancelEvent = SSEEventEnvelope<CancelEventData>;
export type DoneEvent = SSEEventEnvelope<DoneEventData>;
export type ErrorEvent = SSEEventEnvelope<ErrorEventData>;

/**
 * Union type for all typed SSE event envelopes
 */
export type AnySSEEventEnvelope =
  | SessionStartEvent
  | RoutingDecisionEvent
  | PhaseEvent
  | ReasoningEvent
  | MessageEvent
  | ToolCallEvent
  | ToolResultEvent
  | CitationEvent
  | ConfirmationRequiredEvent
  | CancelEvent
  | DoneEvent
  | ErrorEvent;

/**
 * @deprecated Compatibility-only shape for UI components that still consume
 * flattened event records. Transport handlers emit SSEEventEnvelope.
 */
export interface SSEEvent {
  type: SSEEventType;
  content?: any;
  timestamp?: string;
  tool?: string;
  result?: any;
  event?: string;
  data?: any;
  message_id?: string;
}

/**
 * SSE Event Handlers
 *
 * HARD RULE 0.2: message_id is required for event correlation.
 */
export interface SSEHandlers {
  /** Handler for all non-terminal events in canonical envelope format */
  onEnvelope: (event: SSEEventEnvelope) => void;
  /** Handler for errors */
  onError: (error: Error) => void;
  /** Handler for stream completion */
  onDone: (data?: DoneEventData & { iterations?: number }) => void;
}

/**
 * Parse SSE event data into SSEEventEnvelope format
 *
 * HARD RULE 0.2: Extracts message_id from payload.
 * Non-heartbeat events without message_id are treated as protocol errors.
 *
 * @param eventType - Event type from 'event:' line
 * @param payload - parsed JSON data from 'data:' line
 * @returns SSEEventEnvelope with message_id binding
 */
export function parseToEnvelope<T>(eventType: SSEEventType, payload: T): SSEEventEnvelope<T> {
  const messageId = (payload as any).message_id;

  if (!messageId && eventType !== 'heartbeat') {
    throw new Error(`[SSE] Event missing message_id: ${eventType}`);
  }

  return {
    event: eventType,
    data: payload,
    message_id: messageId || '',
  };
}

/**
 * SSE Service Configuration
 */
interface SSEConfig {
  maxReconnects: number;
  heartbeatTimeout: number;
  reconnectBaseDelay: number;
}

const DEFAULT_CONFIG: SSEConfig = {
  maxReconnects: 3,
  heartbeatTimeout: 60000,
  reconnectBaseDelay: 1000,
};

/**
 * SSE Service Class
 *
 * Uses fetch + streaming for POST-based SSE connections.
 * HARD RULE 0.2: Tracks message_id for event correlation.
 */
export class SSEService {
  private abortController: AbortController | null = null;
  private reconnectAttempts = 0;
  private config: SSEConfig;
  private heartbeatTimer: ReturnType<typeof setTimeout> | null = null;
  private lastEventId: string | null = null;
  /** Current message_id for event correlation (HARD RULE 0.2) */
  private currentMessageId: string | null = null;
  private currentUrl: string = '';
  private currentHandlers: SSEHandlers | null = null;
  private currentBody: Record<string, unknown> | null = null;
  private isDisconnecting: boolean = false;

  constructor(config: Partial<SSEConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /**
   * Connect to SSE endpoint using POST
   */
  connect(url: string, handlers: SSEHandlers, body?: Record<string, unknown>): void {
    this.disconnect();
    this.isDisconnecting = false;
    this.currentUrl = url;
    this.currentHandlers = handlers;
    this.currentBody = body || {};
    this.currentMessageId = null; // Reset message_id for new connection
    this.lastEventId = null; // Fresh requests must not carry previous stream cursor
    this.reconnectAttempts = 0;

    this.startStreaming(false);
  }

  /**
   * Get current message_id for event correlation
   * HARD RULE 0.2: Returns the message_id from session_start event
   */
  getCurrentMessageId(): string | null {
    return this.currentMessageId;
  }

  /**
   * Start streaming using fetch API
   */
  private async startStreaming(isReconnect: boolean): Promise<void> {
    if (!this.currentHandlers) return;

    this.abortController = new AbortController();

    try {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
      };

      if (isReconnect && this.lastEventId) {
        headers['Last-Event-ID'] = this.lastEventId;
      }

      const response = await fetch(this.currentUrl, {
        method: 'POST',
        headers,
        body: JSON.stringify(this.currentBody),
        credentials: 'include',
        signal: this.abortController.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      // Connection is healthy again; future failures start a new reconnect chain.
      this.reconnectAttempts = 0;

      this.startHeartbeatMonitor();
      await this.processStream(response);
    } catch (error: any) {
      if (error.name === 'AbortError') {
        return; // Stream aborted (intentional disconnect)
      }
      console.error('[SSE] Connection error:', error);
      if (!this.isDisconnecting) {
        this.handleReconnect();
      }
    }
  }

  /**
   * Process SSE stream line by line
   */
  private async processStream(response: Response): Promise<void> {
    if (!this.currentHandlers) return;

    const reader = response.body?.getReader();
    if (!reader) {
      this.currentHandlers.onError(new Error('No response body'));
      return;
    }

    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          this.processLine(line);
        }
      }

      if (buffer) {
        this.processLine(buffer);
      }

      // A stream can also close without emitting a final `done` event
      // (for example when execution pauses for user confirmation).
      // If we did not intentionally disconnect, surface the closure so the UI
      // can exit the running state instead of staying locked forever.
      if (!this.isDisconnecting && this.currentHandlers) {
        this.currentHandlers.onError(new Error('Stream closed unexpectedly'));
      }
    } catch (error: any) {
      if (error.name !== 'AbortError') {
        this.currentHandlers.onError(error);
      }
    }
  }

  /**
   * Process a single SSE line
   */
  private processLine(line: string): void {
    if (!this.currentHandlers) return;

    this.resetHeartbeat();

    if (line.startsWith('event:')) {
      const eventType = line.slice(7).trim();
      this.currentEventType = eventType;
    } else if (line.startsWith('data:')) {
      const dataStr = line.slice(5).trim();
      if (dataStr && this.currentEventType) {
        this.handleEvent(this.currentEventType, dataStr);
        this.currentEventType = null;
      }
    } else if (line.startsWith('id:')) {
      this.lastEventId = line.slice(3).trim();
    }
  }

  private currentEventType: string | null = null;

  /**
   * Handle a parsed SSE event
   *
   * HARD RULE 0.2: Extracts message_id from payload for event correlation.
   * IMPORTANT: Uses event: line as authoritative type, not JSON.type field.
   *
   * @param eventType - Event type from 'event:' line (authoritative)
   * @param dataStr - JSON data from 'data:' line
   */
  private handleEvent(eventType: string, dataStr: string): void {
    if (!this.currentHandlers) return;

    try {
      // Parse JSON payload from data: line.
      // Backend may send either:
      // 1) Flat payload: { delta, ..., message_id }
      // 2) Wrapped payload: { event, data: { ... }, message_id }
      const rawPayload = JSON.parse(dataStr);

      const isWrappedPayload =
        typeof rawPayload === 'object' &&
        rawPayload !== null &&
        !Array.isArray(rawPayload) &&
        'event' in rawPayload &&
        'data' in rawPayload;

      const payload = isWrappedPayload ? (rawPayload as any).data : rawPayload;

      // Extract message_id (HARD RULE 0.2)
      const messageId =
        (typeof rawPayload === 'object' && rawPayload !== null
          ? (rawPayload as any).message_id
          : undefined) ||
        (typeof payload === 'object' && payload !== null
          ? (payload as any).message_id
          : undefined) ||
        '';
      if (!messageId && eventType !== 'heartbeat') {
        this.currentHandlers.onError(new Error(`[SSE] Event missing message_id: ${eventType}`));
        this.disconnect();
        return;
      }

      // Set currentMessageId from session_start (HARD RULE 0.2)
      if (eventType === 'session_start' && messageId) {
        this.currentMessageId = messageId;
      }

      // Create SSEEventEnvelope format
      const envelope: SSEEventEnvelope = {
        event: eventType as SSEEventType,
        data: payload,
        message_id: messageId,
      };

      // Handle special event types
      if (eventType === 'done') {
        this.isDisconnecting = true;
        const doneData: DoneEventData = {
          finish_reason: (payload as any)?.finish_reason || 'stop',
          tokens_used: (payload as any)?.tokens_used || 0,
          cost: (payload as any)?.cost || 0,
          total_time_ms: (payload as any)?.total_time_ms || 0,
          answer_mode: (payload as any)?.answer_mode,
          claims: (payload as any)?.claims,
          citations: (payload as any)?.citations,
          evidence_blocks: (payload as any)?.evidence_blocks,
          quality: (payload as any)?.quality,
          retrieval_trace_id: (payload as any)?.retrieval_trace_id,
          error_state: (payload as any)?.error_state,
          trace: (payload as any)?.trace,
        };
        this.currentHandlers.onDone({
          ...doneData,
          iterations: (payload as any)?.iterations || 0,
        });
        this.disconnect();
      } else if (eventType === 'error') {
        const errorData: ErrorEventData = {
          code: (payload as any)?.code || 'UNKNOWN',
          message: (payload as any)?.error || (payload as any)?.message || 'Stream error',
          recoverable: (payload as any)?.recoverable ?? false,
        };
        this.currentHandlers.onError(new Error(errorData.message));
        this.disconnect();
      } else if (eventType === 'cancel') {
        // User cancelled the stream
        this.isDisconnecting = true;
        this.currentHandlers.onDone({
          finish_reason: 'cancel',
        });
        this.disconnect();
      } else if (eventType === 'heartbeat') {
        // Keepalive - SSE comment format, ignored
      } else {
        // Emit canonical envelope only.
        this.currentHandlers.onEnvelope(envelope);
      }
    } catch (err) {
      console.error('[SSE] Failed to parse event:', err, dataStr);
    }
  }

  /**
   * Handle reconnection with exponential backoff
   */
  private handleReconnect(): void {
    if (this.isDisconnecting) return;

    if (this.reconnectAttempts < this.config.maxReconnects) {
      const delay = this.config.reconnectBaseDelay * Math.pow(2, this.reconnectAttempts);

      this.reconnectAttempts++;

      setTimeout(() => {
        this.startStreaming(true);
      }, delay);
    } else {
      console.error('[SSE] Max reconnection attempts reached');
      this.currentHandlers?.onError(new Error('Max reconnection attempts reached'));
      this.disconnect();
    }
  }

  /**
   * Start heartbeat monitoring
   */
  private startHeartbeatMonitor(): void {
    this.heartbeatTimer = setTimeout(() => {
      console.warn('[SSE] Heartbeat timeout');
      if (!this.isDisconnecting) {
        this.handleReconnect();
      }
    }, this.config.heartbeatTimeout);
  }

  /**
   * Reset heartbeat timer
   */
  private resetHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearTimeout(this.heartbeatTimer);
    }
    this.startHeartbeatMonitor();
  }

  /**
   * Disconnect from SSE endpoint
   * HARD RULE 0.2: Resets message_id tracking on disconnect.
   */
  disconnect(): void {
    this.isDisconnecting = true;

    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }

    if (this.heartbeatTimer) {
      clearTimeout(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }

    this.reconnectAttempts = 0;
    this.currentUrl = '';
    this.currentHandlers = null;
    this.currentBody = null;
    this.currentMessageId = null; // Reset message_id (HARD RULE 0.2)
  }

  /**
   * Check if currently connected
   */
  isConnected(): boolean {
    return this.abortController !== null && !this.isDisconnecting;
  }

  /**
   * Get last event ID for debugging
   */
  getLastEventId(): string | null {
    return this.lastEventId;
  }
}

/**
 * Singleton instance
 */
export const sseService = new SSEService();
