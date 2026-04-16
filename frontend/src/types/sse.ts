/**
 * SSE Event Type Definitions
 *
 * Server-Sent Events types for Agent-Native Chat real-time streaming.
 * Each event includes contract fields: id, sequence, timestamp, session_id, type, data, and message_id.
 *
 * HARD RULE 0.2: message_id is mandatory for all events.
 * The message_id binds all events in a single AI response stream.
 *
 * Event flow:
 * 1. session_start (first) → establishes message_id binding
 * 2. routing_decision → determines query path
 * 3. phase → phase switching events
 * 4. reasoning → AI reasoning content stream
 * 5. tool_call → tool invocation start
 * 6. tool_result → tool execution result
 * 7. message → final assistant message stream
 * 8. citation → citation information
 * 9. error → error notifications
 * 10. done → stream completion marker
 */

/**
 * SSE event types enumeration
 * Updated to include new event types for HARD RULE 0.2
 */
export enum SSEEventType {
  // Session initialization (HARD RULE 0.2)
  SESSION_START = 'session_start',
  // Routing
  ROUTING_DECISION = 'routing_decision',
  // Phase
  PHASE = 'phase',
  // Content streaming
  REASONING = 'reasoning',
  MESSAGE = 'message',
  // Tool execution
  TOOL_CALL = 'tool_call',
  TOOL_RESULT = 'tool_result',
  // Citations
  CITATION = 'citation',
  // User confirmation
  CONFIRMATION_REQUIRED = 'confirmation_required',
  // Cancellation
  CANCEL = 'cancel',
  // Terminal events
  ERROR = 'error',
  DONE = 'done',
  // Keepalive
  HEARTBEAT = 'heartbeat',
  // Legacy events (deprecated but kept for backward compatibility)
  THINKING_STATUS = 'thinking_status',
  STEP_PROGRESS = 'step_progress',
  THOUGHT = 'thought',
}

/**
 * Thinking status enumeration for status visualization
 * @deprecated Use AgentPhase from @/types/chat instead. Kept for backward compatibility.
 */
export enum ThinkingStatus {
  IDLE = 'idle',
  ANALYZING = 'analyzing',
  RETRIEVING = 'retrieving',
  /** @deprecated Use TOOL_CALLING instead */
  PLANNING = 'tool_calling',
  /** @deprecated Use RETRIEVING instead */
  EXECUTING = 'retrieving',
  SYNTHESIZING = 'synthesizing',
  READING = 'reading',
  TOOL_CALLING = 'tool_calling',
  VERIFYING = 'verifying',
  DONE = 'done',
  ERROR = 'error',
  CANCELLED = 'cancelled',
}

/**
 * Base SSE event interface with contract fields
 * All SSE events must include these fields
 *
 * HARD RULE 0.2: message_id is mandatory for event correlation.
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
  /** Message ID - binds all events in this AI response stream (HARD RULE 0.2) */
  message_id: string;
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
  /** Finish reason */
  finish_reason?: 'stop' | 'tool_calls' | 'length' | 'cancel';
  /** Total events in stream */
  total_events?: number;
  /** Total processing duration in milliseconds */
  total_duration?: number;
  /** Final token usage summary */
  tokens_used?: number;
  /** Session completion status */
  completion_status?: 'success' | 'partial' | 'failed';
}

/**
 * Session Start Data
 * First event in stream, establishes message_id binding (HARD RULE 0.2)
 */
export interface SessionStartData {
  session_id: string;
  task_type: 'single_paper' | 'kb_qa' | 'compare' | 'general';
  message_id: string;
}

/**
 * Phase Data
 * Indicates current agent processing phase
 */
export interface PhaseData {
  phase: 'analyze' | 'plan' | 'execute' | 'synthesize' | 'respond';
  label: string;
}

/**
 * Reasoning Data (streaming)
 * AI thinking content - incremental deltas
 */
export interface ReasoningData {
  delta: string;
  seq: number;
}

/**
 * Citation Data
 * Reference to source paper
 */
export interface CitationData {
  paper_id: string;
  title: string;
  pages: number[];
  hits: number;
}

/**
 * Confirmation Required Data
 * Dangerous operation needs user approval
 */
export interface ConfirmationRequiredData {
  operation: string;
  risk_level: 'low' | 'medium' | 'high';
  details: string;
}

/**
 * Cancel Data
 * User cancelled the stream
 */
export interface CancelData {
  reason: 'user_stop' | 'timeout' | 'network_error';
}

/**
 * Typed SSE event variants
 * Use these for specific event handling
 */
export type SessionStartEvent = SSEEvent<SessionStartData>;
export type RoutingDecisionEvent = SSEEvent<RoutingDecisionData>;
export type PhaseEvent = SSEEvent<PhaseData>;
export type ReasoningEvent = SSEEvent<ReasoningData>;
export type ThinkingStatusEvent = SSEEvent<ThinkingStatusData>;
export type StepProgressEvent = SSEEvent<StepProgressData>;
export type ThoughtEvent = SSEEvent<ThoughtData>;
export type ToolCallEvent = SSEEvent<ToolCallData>;
export type ToolResultEvent = SSEEvent<ToolResultData>;
export type MessageEvent = SSEEvent<MessageData>;
export type CitationEvent = SSEEvent<CitationData>;
export type ConfirmationRequiredEvent = SSEEvent<ConfirmationRequiredData>;
export type CancelEvent = SSEEvent<CancelData>;
export type ErrorEvent = SSEEvent<ErrorData>;
export type DoneEvent = SSEEvent<DoneData>;

/**
 * Union type for all SSE events
 */
export type AnySSEEvent =
  | SessionStartEvent
  | RoutingDecisionEvent
  | PhaseEvent
  | ReasoningEvent
  | ThinkingStatusEvent
  | StepProgressEvent
  | ThoughtEvent
  | ToolCallEvent
  | ToolResultEvent
  | MessageEvent
  | CitationEvent
  | ConfirmationRequiredEvent
  | CancelEvent
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
 * Ensures all contract fields are present, including message_id (HARD RULE 0.2)
 */
export function createSSEEvent<T>(
  type: SSEEventType,
  data: T,
  sessionId: string,
  sequence: number,
  messageId?: string
): SSEEvent<T> {
  return {
    id: crypto.randomUUID(),
    sequence,
    timestamp: Date.now(),
    session_id: sessionId,
    type,
    data,
    message_id: messageId || crypto.randomUUID(), // Generate if not provided
  };
}