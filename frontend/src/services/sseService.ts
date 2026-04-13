/**
 * SSE Service with Auto-Reconnect
 *
 * Manages Server-Sent Events connections with:
 * - POST-based streaming (fetch API)
 * - Automatic reconnection with exponential backoff (3 retries)
 * - Heartbeat monitoring (60s timeout)
 * - Last-Event-ID support for resumption
 * - Proper cleanup on disconnect
 *
 * Event types from backend:
 * - thought: Agent thinking process
 * - tool_call: Agent invoking tool
 * - tool_result: Tool execution result
 * - confirmation_required: Dangerous operation needs approval
 * - message: Final response
 * - done: Stream complete
 * - heartbeat: 15s keepalive
 */

/**
 * SSE Event Types (from backend Agent-Native architecture)
 * These come from the 'event:' line in SSE stream
 *
 * P2 additions:
 * - routing_decision: Agent routing decision (complexity analysis)
 * - thinking_status: Thinking process status updates
 */
export type SSEEventType =
  | 'thought'
  | 'tool_call'
  | 'tool_result'
  | 'confirmation_required'
  | 'message'
  | 'done'
  | 'heartbeat'
  | 'error'
  | 'citation'
  | 'routing_decision'
  | 'thinking_status';

/**
 * SSE Event structure
 * 
 * IMPORTANT: 'type' field comes from 'event:' line (authoritative), not from JSON.type
 * 'content' field contains the entire JSON payload from 'data:' line
 */
export interface SSEEvent {
  /** Event type from 'event:' line - authoritative source */
  type: SSEEventType;
  /** Entire JSON payload from 'data:' line */
  content: any;
  /** Optional timestamp from payload */
  timestamp?: string;
  /** Tool name for tool_call/tool_result events */
  tool?: string;
  /** Tool result for tool_result events */
  result?: any;
  /** Event type string (same as type, for backward compatibility) */
  event?: string;
  /** Raw data payload (same as content, for backward compatibility) */
  data?: any;
}

/**
 * SSE Event Handlers
 */
export interface SSEHandlers {
  onMessage: (event: SSEEvent) => void;
  onError: (error: Error) => void;
  onDone: (data?: { tokens_used?: number; cost?: number; iterations?: number; total_time_ms?: number; citations?: any[] }) => void;
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
 */
export class SSEService {
  private abortController: AbortController | null = null;
  private reconnectAttempts = 0;
  private config: SSEConfig;
  private heartbeatTimer: ReturnType<typeof setTimeout> | null = null;
  private lastEventId: string | null = null;
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

    this.startStreaming();
  }

  /**
   * Start streaming using fetch API
   */
  private async startStreaming(): Promise<void> {
    if (!this.currentHandlers) return;

    this.abortController = new AbortController();
    this.reconnectAttempts = 0;

    try {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
      };

      if (this.lastEventId) {
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
   * IMPORTANT: Uses event: line as authoritative type, not JSON.type field
   */
  private handleEvent(eventType: string, dataStr: string): void {
    if (!this.currentHandlers) return;

    try {
      // Parse JSON payload from data: line
      const payload = JSON.parse(dataStr);

      // Construct SSEEvent using event: line type as authoritative
      // This fixes the bug where frontend used JSON.type instead of SSE event type
      const event: SSEEvent = {
        type: eventType as SSEEventType,  // From event: line (authoritative)
        content: payload,                 // Entire JSON payload
        timestamp: payload.timestamp,
        tool: payload.tool,
        result: payload.result || payload.data,
        event: eventType,
        data: payload,
      };

      // Store last event ID if present
      if (this.lastEventId) {
        // Already stored in processLine() at line 206
      }

      if (eventType === 'done') {
        this.isDisconnecting = true;
        const tokensUsed = payload.tokens_used || 0;
        const cost = payload.cost || 0;
        const iterations = payload.iterations || 0;
        const total_time_ms = payload.total_time_ms || 0;
        this.currentHandlers.onDone({
          tokens_used: tokensUsed,
          cost,
          iterations,
          total_time_ms,
        });
        this.disconnect();
      } else if (eventType === 'error') {
        this.currentHandlers.onError(
          new Error(payload.error || payload.message || 'Stream error')
        );
        this.disconnect();
      } else if (eventType === 'heartbeat') {
        // Keepalive - SSE comment format, ignored
      } else {
        this.currentHandlers.onMessage(event);
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

      setTimeout(() => {
        this.reconnectAttempts++;
        this.startStreaming();
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
