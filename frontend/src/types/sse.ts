/**
 * SSE Event Type Definitions
 *
 * Server-Sent Events types for Agent-Native Chat real-time streaming.
 * Each event includes contract fields: id, sequence, timestamp, session_id, type, and data.
 *
 * Event flow:
 * 1. routing_decision (first) → determines query path
 * 2. thinking_status → status updates (idle/analyzing/planning/executing/synthesizing)
 * 3. step_progress → step completion updates
 * 4. thought → AI reasoning content
 * 5. tool_call → tool invocation start
 * 6. tool_result → tool execution result
 * 7. message → final assistant message
 * 8. error → error notifications
 * 9. done → stream completion marker
 */

/**
 * SSE event types enumeration
 */
export enum SSEEventType {
  ROUTING_DECISION = 'routing_decision',
  THINKING_STATUS = 'thinking_status',
  STEP_PROGRESS = 'step_progress',
  THOUGHT = 'thought',
  TOOL_CALL = 'tool_call',
  TOOL_RESULT = 'tool_result',
  MESSAGE = 'message',
  ERROR = 'error',
  DONE = 'done',
}

/**
 * Thinking status enumeration for status visualization
 */
export enum ThinkingStatus {
  IDLE = 'idle',
  ANALYZING = 'analyzing',
  PLANNING = 'planning',
  EXECUTING = 'executing',
  SYNTHESIZING = 'synthesizing',
}

/**
 * Base SSE event interface with contract fields
 * All SSE events must include these fields
 */
export interface SSEEvent<T = unknown> {
  /** Unique event identifier (UUID) */
  id: string;
  /** Event sequence number within the session */
  sequence: number;
  /** Event timestamp (Unix milliseconds) */
  timestamp: number;
  /** Session identifier for correlation */
  session_id: string;
  /** Event type discriminator */
  type: SSEEventType;
  /** Event-specific payload */
  data: T;
}

/**
 * Routing decision data
 * First event in stream, determines query processing path
 */
export interface RoutingDecisionData {
  /** Selected routing path */
  route: 'rag' | 'knowledge_graph' | 'hybrid' | 'external_search' | 'clarification';
  /** Confidence score (0-1) */
  confidence: number;
  /** Reason for routing decision */
  reason: string;
  /** Estimated steps count */
  estimated_steps?: number;
  /** Alternative routes considered */
  alternatives?: Array<{
    route: string;
    confidence: number;
  }>;
}

/**
 * Thinking status data
 * Status updates for thinking visualization component
 */
export interface ThinkingStatusData {
  /** Current thinking status */
  status: ThinkingStatus;
  /** Human-readable status message */
  message?: string;
  /** Progress percentage (0-100) */
  progress?: number;
  /** Current step being processed */
  current_step?: string;
}

/**
 * Step progress data
 * Tracks completion of processing steps
 */
export interface StepProgressData {
  /** Step identifier */
  step_id: string;
  /** Step name/type */
  step_name: string;
  /** Step status */
  status: 'started' | 'in_progress' | 'completed' | 'failed';
  /** Step duration in milliseconds */
  duration?: number;
  /** Progress percentage (0-100) */
  progress?: number;
  /** Step-specific details */
  details?: Record<string, unknown>;
}

/**
 * Thought data
 * AI reasoning content for thought visualization
 */
export interface ThoughtData {
  /** Thought content (markdown) */
  content: string;
  /** Thought type/category */
  thought_type?: 'analysis' | 'reasoning' | 'reflection' | 'planning';
  /** Related step if applicable */
  step_id?: string;
}

/**
 * Tool call data
 * Tool invocation start event
 */
export interface ToolCallData {
  /** Tool call identifier */
  tool_call_id: string;
  /** Tool name */
  tool_name: string;
  /** Tool parameters */
  parameters: Record<string, unknown>;
  /** Tool display name for UI */
  display_name?: string;
  /** Expected duration hint */
  estimated_duration?: number;
}

/**
 * Tool result data
 * Tool execution result event
 */
export interface ToolResultData {
  /** Correlation with tool call */
  tool_call_id: string;
  /** Tool name */
  tool_name: string;
  /** Execution status */
  status: 'success' | 'error' | 'timeout';
  /** Result payload */
  result?: unknown;
  /** Error message if failed */
  error?: string;
  /** Execution duration in milliseconds */
  duration: number;
}

/**
 * Message data
 * Final assistant message content
 */
export interface MessageData {
  /** Message content (markdown) */
  content: string;
  /** Citations array */
  citations?: Array<{
    paper_id: string;
    title: string;
    snippet: string;
    page?: number;
  }>;
  /** Token usage for this message */
  tokens_used?: number;
}

/**
 * Error data
 * Error notification event
 */
export interface ErrorData {
  /** Error code */
  code: string;
  /** Error message */
  message: string;
  /** Error severity */
  severity: 'warning' | 'error' | 'critical';
  /** Error details */
  details?: Record<string, unknown>;
  /** Whether error is recoverable */
  recoverable?: boolean;
}

/**
 * Done data
 * Stream completion marker
 */
export interface DoneData {
  /** Total events in stream */
  total_events?: number;
  /** Total processing duration in milliseconds */
  total_duration?: number;
  /** Final token usage summary */
  tokens_used?: number;
  /** Session completion status */
  completion_status: 'success' | 'partial' | 'failed';
}

/**
 * Typed SSE event variants
 * Use these for specific event handling
 */
export type RoutingDecisionEvent = SSEEvent<RoutingDecisionData>;
export type ThinkingStatusEvent = SSEEvent<ThinkingStatusData>;
export type StepProgressEvent = SSEEvent<StepProgressData>;
export type ThoughtEvent = SSEEvent<ThoughtData>;
export type ToolCallEvent = SSEEvent<ToolCallData>;
export type ToolResultEvent = SSEEvent<ToolResultData>;
export type MessageEvent = SSEEvent<MessageData>;
export type ErrorEvent = SSEEvent<ErrorData>;
export type DoneEvent = SSEEvent<DoneData>;

/**
 * Union type for all SSE events
 */
export type AnySSEEvent =
  | RoutingDecisionEvent
  | ThinkingStatusEvent
  | StepProgressEvent
  | ThoughtEvent
  | ToolCallEvent
  | ToolResultEvent
  | MessageEvent
  | ErrorEvent
  | DoneEvent;

/**
 * Type guard for SSE event type checking
 */
export function isSSEEventOfType<T>(
  event: SSEEvent,
  eventType: SSEEventType
): event is SSEEvent<T> {
  return event.type === eventType;
}

/**
 * Helper to create a valid SSE event
 * Ensures all contract fields are present
 */
export function createSSEEvent<T>(
  type: SSEEventType,
  data: T,
  sessionId: string,
  sequence: number
): SSEEvent<T> {
  return {
    id: crypto.randomUUID(),
    sequence,
    timestamp: Date.now(),
    session_id: sessionId,
    type,
    data,
  };
}