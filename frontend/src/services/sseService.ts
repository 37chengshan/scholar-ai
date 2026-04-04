/**
 * SSE Service with Auto-Reconnect
 *
 * Manages Server-Sent Events connections with:
 * - Automatic reconnection with exponential backoff (3 retries)
 * - Heartbeat monitoring (15s timeout)
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
  | 'heartbeat';

/**
 * SSE Event structure
 */
export interface SSEEvent {
  type: SSEEventType;
  content: any;
  timestamp?: string;
  tool?: string; // For tool_call/tool_result
  result?: any; // For tool_result
}

/**
 * SSE Event Handlers
 */
export interface SSEHandlers {
  onMessage: (event: SSEEvent) => void;
  onError: (error: Error) => void;
  onDone: () => void;
}

/**
 * SSE Service Configuration
 */
interface SSEConfig {
  maxReconnects: number;
  heartbeatTimeout: number; // ms
  reconnectBaseDelay: number; // ms
}

const DEFAULT_CONFIG: SSEConfig = {
  maxReconnects: 3,
  heartbeatTimeout: 15000, // 15s per D-05
  reconnectBaseDelay: 1000, // 1s base for exponential backoff
};

/**
 * SSE Service Class
 *
 * Manages EventSource connections with automatic reconnection
 * and heartbeat monitoring.
 *
 * Usage:
 * ```typescript
 * const sseService = new SSEService();
 *
 * sseService.connect('/api/chat/stream?message=hello', {
 *   onMessage: (event) => console.log('Event:', event),
 *   onError: (err) => console.error('Error:', err),
 *   onDone: () => console.log('Stream complete'),
 * });
 *
 * // Later...
 * sseService.disconnect();
 * ```
 */
export class SSEService {
  private eventSource: EventSource | null = null;
  private reconnectAttempts = 0;
  private config: SSEConfig;
  private heartbeatTimer: ReturnType<typeof setTimeout> | null = null;
  private lastEventId: string | null = null;
  private currentUrl: string = '';
  private currentHandlers: SSEHandlers | null = null;

  constructor(config: Partial<SSEConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /**
   * Connect to SSE endpoint
   *
   * @param url - SSE endpoint URL
   * @param handlers - Event handlers (onMessage, onError, onDone)
   */
  connect(url: string, handlers: SSEHandlers): void {
    // Disconnect any existing connection
    this.disconnect();

    // Store for reconnection
    this.currentUrl = url;
    this.currentHandlers = handlers;

    // Build URL with Last-Event-ID for resumption
    const eventSourceUrl = this.lastEventId
      ? `${url}${url.includes('?') ? '&' : '?'}last_event_id=${this.lastEventId}`
      : url;

    // Create EventSource with credentials for Cookie-based auth
    this.eventSource = new EventSource(eventSourceUrl, {
      withCredentials: true,
    });

    // Reset reconnect attempts on new connection
    this.reconnectAttempts = 0;

    // Set up event handlers
    this.setupEventHandlers(handlers);

    // Start heartbeat monitoring
    this.startHeartbeatMonitor();
  }

  /**
   * Set up EventSource event handlers
   */
  private setupEventHandlers(handlers: SSEHandlers): void {
    if (!this.eventSource) return;

    // Handle incoming messages
    this.eventSource.onmessage = (e: MessageEvent) => {
      this.resetHeartbeat();

      try {
        const event: SSEEvent = JSON.parse(e.data);

        // Store Last-Event-ID for reconnection
        if (e.lastEventId) {
          this.lastEventId = e.lastEventId;
        }

        // Handle different event types
        if (event.type === 'done') {
          handlers.onDone();
          this.disconnect();
        } else if (event.type === 'heartbeat') {
          // Heartbeat received, connection is alive
          // Already reset heartbeat timer above
        } else {
          // Forward to handler
          handlers.onMessage(event);
        }
      } catch (err) {
        console.error('[SSE] Failed to parse event:', err, e.data);
      }
    };

    // Handle errors (connection drops, etc.)
    this.eventSource.onerror = () => {
      console.error('[SSE] Connection error');

      // Attempt reconnection
      this.handleReconnect();
    };

    // Connection opened
    this.eventSource.onopen = () => {
      console.log('[SSE] Connection established');
      this.reconnectAttempts = 0;
    };
  }

  /**
   * Handle reconnection with exponential backoff
   */
  private handleReconnect(): void {
    if (this.reconnectAttempts < this.config.maxReconnects) {
      // Calculate delay with exponential backoff: 1s, 2s, 4s
      const delay = this.config.reconnectBaseDelay * Math.pow(2, this.reconnectAttempts);

      console.log(
        `[SSE] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts + 1}/${this.config.maxReconnects})`
      );

      // Close existing connection
      if (this.eventSource) {
        this.eventSource.close();
        this.eventSource = null;
      }

      // Schedule reconnection
      setTimeout(() => {
        this.reconnectAttempts++;

        if (this.currentUrl && this.currentHandlers) {
          this.connect(this.currentUrl, this.currentHandlers);
        }
      }, delay);
    } else {
      // Max reconnection attempts reached
      console.error('[SSE] Max reconnection attempts reached');

      if (this.currentHandlers) {
        this.currentHandlers.onError(new Error('Max reconnection attempts reached'));
      }

      this.disconnect();
    }
  }

  /**
   * Start heartbeat monitoring
   *
   * If no event received within heartbeatTimeout, trigger reconnection
   */
  private startHeartbeatMonitor(): void {
    this.heartbeatTimer = setTimeout(() => {
      console.warn('[SSE] Heartbeat timeout - no event received');
      this.handleReconnect();
    }, this.config.heartbeatTimeout);
  }

  /**
   * Reset heartbeat timer
   *
   * Called when any event is received
   */
  private resetHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearTimeout(this.heartbeatTimer);
    }
    this.startHeartbeatMonitor();
  }

  /**
   * Disconnect from SSE endpoint
   *
   * Cleans up EventSource and timers
   */
  disconnect(): void {
    // Close EventSource
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }

    // Clear heartbeat timer
    if (this.heartbeatTimer) {
      clearTimeout(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }

    // Reset state
    this.reconnectAttempts = 0;
    this.currentUrl = '';
    this.currentHandlers = null;
  }

  /**
   * Check if currently connected
   */
  isConnected(): boolean {
    return this.eventSource !== null && this.eventSource.readyState === EventSource.OPEN;
  }

  /**
   * Get last event ID for debugging
   */
  getLastEventId(): string | null {
    return this.lastEventId;
  }
}

/**
 * Singleton instance for global use
 */
export const sseService = new SSEService();