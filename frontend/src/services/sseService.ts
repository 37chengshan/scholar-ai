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
  | 'citation';

/**
 * SSE Event structure
 */
export interface SSEEvent {
  type: SSEEventType;
  content: any;
  timestamp?: string;
  tool?: string;
  result?: any;
  event?: string;
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
   */
  private handleEvent(eventType: string, dataStr: string): void {
    if (!this.currentHandlers) return;

    try {
      const event: SSEEvent = JSON.parse(dataStr);

      if (eventType === 'done') {
        this.isDisconnecting = true;
        const tokensUsed = (event as any).tokens_used || (event as any).content?.tokens_used || 0;
        const cost = (event as any).cost || (event as any).content?.cost || 0;
        const iterations = (event as any).iterations || (event as any).content?.iterations || 0;
        const total_time_ms = (event as any).total_time_ms || (event as any).content?.total_time_ms || 0;
        this.currentHandlers.onDone({
          tokens_used: tokensUsed,
          cost,
          iterations,
          total_time_ms,
        });
        this.disconnect();
      } else if (eventType === 'heartbeat') {
        // Keepalive
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