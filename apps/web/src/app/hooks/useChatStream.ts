/**
 * useChatStream Hook - State Machine + Buffer + Force Flush
 *
 * Implements Agent-Native Chat streaming with:
 * - State machine with status guards (idle/streaming/completed/error/cancelled)
 * - Separate buffers for reasoning and content (HARD RULE 0.4)
 * - 100ms throttle for batch UI updates
 * - Force flush on done/error/cancel/unmount
 * - message_id validation to ignore stale events (HARD RULE 0.2)
 *
 * HARD RULES:
 * - 0.2: Every SSE event MUST carry message_id, frontend MUST validate
 * - 0.3: State machine guards - completed/error/cancelled ignore streaming events
 * - 0.4: Separate buffers for reasoning (think panel) and content (assistant message)
 */

import { useReducer, useRef, useCallback, useEffect } from 'react';
import { trackStreamEvent } from '@/lib/observability/telemetry';

// ============================================================================
// Type Definitions
// ============================================================================

/**
 * Agent phase enumeration for phase tracking
 */
import { AgentPhase, StreamStatus } from '@/types/chat';

// Re-export StreamStatus for backward compatibility
export type { StreamStatus };

/**
 * Task type for session context
 */
export type TaskType =
  | 'single_paper'
  | 'kb_qa'
  | 'compare'
  | 'general';

/**
 * Tool timeline item for tracking tool calls
 */
export interface ToolTimelineItem {
  id: string;
  tool: string;
  label: string;
  status: 'pending' | 'running' | 'success' | 'error';
  startedAt: number;
  completedAt?: number;
  duration?: number;
  summary?: string;
}

/**
 * Citation item for reference tracking
 */
export interface CitationItem {
  paper_id: string;
  title: string;
  authors: string[];
  year: number;
  snippet: string;
  page?: number;
  score: number;
  content_type: 'text' | 'table' | 'figure';
  chunk_id?: string;
}

/**
 * ChatStreamState - Complete state structure
 */
export interface ChatStreamState {
  // HARD RULE 0.2: Message binding
  messageId: string;

  // HARD RULE 0.3: State machine
  streamStatus: StreamStatus;

  // Session context
  sessionId?: string;
  taskType: TaskType;

  // Phase tracking
  currentPhase: AgentPhase;
  phaseLabel: string;

  // HARD RULE 0.4: Separate buffers
  reasoningBuffer: string;   // For think panel and right sidebar
  contentBuffer: string;     // For assistant message body

  // Tool timeline
  toolTimeline: ToolTimelineItem[];

  // Citations
  citations: CitationItem[];

  // Confirmation (agent tool approval)
  confirmation: ConfirmationState | null;

  // Timing
  startedAt?: number;
  endedAt?: number;

  // Error state
  error?: {
    code: string;
    message: string;
  };

  // Metrics
  tokensUsed: number;
  cost: number;
}

/**
 * Confirmation request from agent (for dangerous tool approval)
 */
export interface ConfirmationState {
  confirmation_id: string;  // Required for backend resumption
  tool: string;
  params: Record<string, unknown>;
}

/**
 * SSE Action types for state transitions
 */
export type SSEAction =
  | { type: 'SESSION_START'; sessionId: string; taskType: TaskType; messageId: string }
  | { type: 'PHASE_CHANGE'; phase: AgentPhase; label: string }
  | { type: 'REASONING_CHUNK'; delta: string }
  | { type: 'MESSAGE_CHUNK'; delta: string }
  | { type: 'TOOL_CALL'; id: string; tool: string; label: string }
  | { type: 'TOOL_RESULT'; id: string; status: string; summary?: string }
  | { type: 'CITATION'; citation: CitationItem }
  | { type: 'CONFIRMATION_REQUIRED'; confirmation: ConfirmationState }
  | { type: 'CONFIRMATION_RESET' }
  | { type: 'STREAM_COMPLETE'; tokensUsed: number; cost: number; durationMs: number }
  | { type: 'ERROR'; code: string; message: string }
  | { type: 'CANCEL'; reason: string }
  | { type: 'RESET' };

/**
 * SSE event envelope from backend
 */
export interface SSEEventEnvelope {
  message_id: string;
  event_type: string;
  data: unknown;
  sequence?: number;
  timestamp?: number;
}

// ============================================================================
// Initial State
// ============================================================================

/**
 * Create initial state
 */
export function createInitialState(): ChatStreamState {
  return {
    messageId: '',
    streamStatus: 'idle',
    sessionId: undefined,
    taskType: 'general',
    currentPhase: 'idle',
    phaseLabel: '准备就绪',
    reasoningBuffer: '',
    contentBuffer: '',
    toolTimeline: [],
    citations: [],
    confirmation: null,
    startedAt: undefined,
    endedAt: undefined,
    error: undefined,
    tokensUsed: 0,
    cost: 0,
  };
}

// ============================================================================
// State Machine Reducer
// ============================================================================

/**
 * State machine reducer with guards
 *
 * HARD RULE 0.3: Ignore streaming events when in terminal states
 */
export function chatStreamReducer(
  state: ChatStreamState,
  action: SSEAction
): ChatStreamState {
  const terminalStates: StreamStatus[] = ['completed', 'error', 'cancelled'];

  // State machine guards - ignore streaming events in terminal states
  if (terminalStates.includes(state.streamStatus)) {
    // Only allow RESET in terminal states
    if (action.type !== 'RESET') {
      console.warn(
        `[chatStreamReducer] Ignoring action ${action.type} in terminal state ${state.streamStatus}`
      );
      return state;
    }
  }

  switch (action.type) {
    case 'SESSION_START':
      return {
        ...state,
        messageId: action.messageId,
        sessionId: action.sessionId,
        taskType: action.taskType,
        streamStatus: 'streaming',
        currentPhase: 'idle',
        phaseLabel: '会话开始',
        startedAt: Date.now(),
        endedAt: undefined,
        error: undefined,
        tokensUsed: 0,
        cost: 0,
        reasoningBuffer: '',
        contentBuffer: '',
        toolTimeline: [],
        citations: [],
      };

    case 'PHASE_CHANGE':
      return {
        ...state,
        currentPhase: action.phase,
        phaseLabel: action.label,
      };

    case 'REASONING_CHUNK':
      return {
        ...state,
        reasoningBuffer: state.reasoningBuffer + action.delta,
      };

    case 'MESSAGE_CHUNK':
      return {
        ...state,
        contentBuffer: state.contentBuffer + action.delta,
      };

    case 'TOOL_CALL':
      return {
        ...state,
        toolTimeline: [
          ...state.toolTimeline,
          {
            id: action.id,
            tool: action.tool,
            label: action.label,
            status: 'running',
            startedAt: Date.now(),
          },
        ],
      };

    case 'TOOL_RESULT':
      return {
        ...state,
        toolTimeline: state.toolTimeline.map((item) =>
          item.id === action.id
            ? {
                ...item,
                status: action.status as 'success' | 'error',
                completedAt: Date.now(),
                duration: Date.now() - item.startedAt,
                summary: action.summary,
              }
            : item
        ),
      };

    case 'CITATION':
      return {
        ...state,
        citations: [...state.citations, action.citation],
      };

    case 'CONFIRMATION_REQUIRED':
      return {
        ...state,
        confirmation: action.confirmation,
      };

    case 'CONFIRMATION_RESET':
      return {
        ...state,
        confirmation: null,
      };

    case 'STREAM_COMPLETE':
      return {
        ...state,
        streamStatus: 'completed',
        currentPhase: 'done',
        phaseLabel: '完成',
        endedAt: Date.now(),
        tokensUsed: action.tokensUsed,
        cost: action.cost,
      };

    case 'ERROR':
      return {
        ...state,
        streamStatus: 'error',
        currentPhase: 'error',
        phaseLabel: '出错',
        endedAt: Date.now(),
        error: {
          code: action.code,
          message: action.message,
        },
      };

    case 'CANCEL':
      return {
        ...state,
        streamStatus: 'cancelled',
        currentPhase: 'cancelled',
        phaseLabel: '已取消',
        endedAt: Date.now(),
      };

    case 'RESET':
      return createInitialState();

    default:
      return state;
  }
}

// ============================================================================
// Hook Implementation
// ============================================================================

/**
 * useChatStream Hook options
 */
export interface UseChatStreamOptions {
  /** Throttle interval in milliseconds (default: 100ms) */
  throttleMs?: number;
  /** Callback when phase changes */
  onPhaseChange?: (phase: AgentPhase, label: string) => void;
  /** Callback when stream completes */
  onComplete?: (state: ChatStreamState) => void;
  /** Callback on error */
  onError?: (error: { code: string; message: string }) => void;
  /** Callback on tool call */
  onToolCall?: (tool: ToolTimelineItem) => void;
}

/**
 * useChatStream Hook return type
 */
export interface UseChatStreamReturn {
  /** Current state */
  state: ChatStreamState;
  /** Dispatch action (for testing or manual control) */
  dispatch: (action: SSEAction) => void;
  /** Start streaming session */
  startStream: (sessionId: string, taskType: TaskType, messageId: string) => void;
  /** Handle SSE event from backend */
  handleSSEEvent: (envelope: SSEEventEnvelope) => void;
  /** Cancel current stream */
  cancelStream: (reason?: string) => void;
  /** Reset to initial state */
  reset: () => void;
  /** Force flush buffers (for done/error/cancel/unmount) */
  forceFlush: () => void;
  /** Current message ID for validation */
  currentMessageId: string;
  /** Get buffered content (may be ahead of state.contentBuffer due to throttle) */
  getBufferedContent: () => { content: string; reasoning: string };
  /** Current confirmation request (null if none) */
  confirmation: ConfirmationState | null;
  /** Reset confirmation state */
  resetConfirmation: () => void;
}

/**
 * useChatStream Hook
 *
 * Implements state machine + buffer + throttle + force flush
 */
export function useChatStream(
  options: UseChatStreamOptions = {}
): UseChatStreamReturn {
  const { throttleMs = 100, onPhaseChange, onComplete, onError, onToolCall } = options;

  // State machine
  const [state, dispatch] = useReducer(chatStreamReducer, createInitialState());

  // Buffer refs for throttling
  const reasoningRef = useRef<string>('');
  const contentRef = useRef<string>('');
  const throttleTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Message ID ref for validation (HARD RULE 0.2)
  const messageIdRef = useRef<string>('');

  // ============================================================================
  // Force Flush (HARD RULE 0.4)
  // ============================================================================

  /**
   * Force flush all buffered content
   * Called on done/error/cancel/unmount to ensure all content is rendered
   */
  const forceFlush = useCallback(() => {
    // Flush reasoning buffer
    if (reasoningRef.current) {
      dispatch({ type: 'REASONING_CHUNK', delta: reasoningRef.current });
      reasoningRef.current = '';
    }

    // Flush content buffer
    if (contentRef.current) {
      dispatch({ type: 'MESSAGE_CHUNK', delta: contentRef.current });
      contentRef.current = '';
    }

    // Clear throttle timer
    if (throttleTimerRef.current) {
      clearTimeout(throttleTimerRef.current);
      throttleTimerRef.current = null;
    }
  }, []);

  // ============================================================================
  // Buffer + Throttle
  // ============================================================================

  /**
   * Schedule throttled flush
   */
  const scheduleFlush = useCallback(() => {
    if (throttleTimerRef.current) {
      console.debug('[useChatStream] scheduleFlush: timer already active, skipping');
      return; // Already scheduled
    }

    console.debug('[useChatStream] scheduleFlush: setting timer for', throttleMs, 'ms');
    throttleTimerRef.current = setTimeout(() => {
      console.debug('[useChatStream] FLUSH TIMER EXECUTING');
      // Flush both buffers
      if (reasoningRef.current) {
        dispatch({ type: 'REASONING_CHUNK', delta: reasoningRef.current });
        reasoningRef.current = '';
      }
      if (contentRef.current) {
        dispatch({ type: 'MESSAGE_CHUNK', delta: contentRef.current });
        contentRef.current = '';
      }
      throttleTimerRef.current = null;
    }, throttleMs);
  }, [throttleMs]);

  /**
   * Buffered dispatch - accumulates chunks and flushes on throttle or terminal action
   */
  const bufferedDispatch = useCallback(
    (action: SSEAction) => {
      // Chunk actions go to buffer
      if (action.type === 'REASONING_CHUNK') {
        reasoningRef.current += action.delta;
        scheduleFlush();
        return;
      }

      if (action.type === 'MESSAGE_CHUNK') {
        contentRef.current += action.delta;
        console.debug('[useChatStream] MESSAGE_CHUNK buffered');
        scheduleFlush();
        return;
      }

      // Terminal actions require immediate flush then dispatch
      const terminalActions = ['STREAM_COMPLETE', 'ERROR', 'CANCEL'];
      if (terminalActions.includes(action.type)) {
        forceFlush();
        dispatch(action);

        // Call callbacks
        if (action.type === 'STREAM_COMPLETE' && onComplete) {
          // onComplete will be called after state update
        }
        if (action.type === 'ERROR' && onError) {
          const errorAction = action as { type: 'ERROR'; code: string; message: string };
          onError({ code: errorAction.code, message: errorAction.message });
        }
        return;
      }

      // All other actions dispatch immediately
      dispatch(action);

      // Call callbacks for phase change
      if (action.type === 'PHASE_CHANGE' && onPhaseChange) {
        const phaseAction = action as { type: 'PHASE_CHANGE'; phase: AgentPhase; label: string };
        onPhaseChange(phaseAction.phase, phaseAction.label);
      }

      // Call callback for tool call
      if (action.type === 'TOOL_CALL' && onToolCall) {
        const toolAction = action as { type: 'TOOL_CALL'; id: string; tool: string; label: string };
        onToolCall({
          id: toolAction.id,
          tool: toolAction.tool,
          label: toolAction.label,
          status: 'running',
          startedAt: Date.now(),
        });
      }
    },
    [forceFlush, scheduleFlush, onPhaseChange, onComplete, onError, onToolCall]
  );

  // ============================================================================
  // Message ID Validation (HARD RULE 0.2)
  // ============================================================================

  /**
   * Handle SSE event from backend
   * Validates message_id and converts to appropriate action
   */
  const handleSSEEvent = useCallback(
    (envelope: SSEEventEnvelope) => {
      // HARD RULE 0.2: message_id validation (skip for session_start which initializes it)
      const eventType = envelope.event_type;
      if (eventType !== 'session_start' && envelope.message_id !== messageIdRef.current) {
        trackStreamEvent({
          event: 'stale_event_ignored',
          expectedMessageId: messageIdRef.current,
          receivedMessageId: envelope.message_id,
          eventType,
        });
        console.warn(
          `[useChatStream] SSE event message_id mismatch. Expected: ${messageIdRef.current}, Got: ${envelope.message_id}. Ignoring.`
        );
        return;
      }

      // Convert envelope to action based on event_type
      const data = envelope.data as Record<string, unknown>;

      switch (eventType) {
        case 'session_start':
          // Initialize message_id binding
          messageIdRef.current = envelope.message_id;
          bufferedDispatch({
            type: 'SESSION_START',
            sessionId: data.session_id as string,
            taskType: (data.task_type as TaskType) || 'general',
            messageId: envelope.message_id,
          });
          trackStreamEvent({
            event: 'stream_started',
            sessionId: data.session_id as string,
            messageId: envelope.message_id,
          });
          break;

        case 'phase':
        case 'phase_change':
          bufferedDispatch({
            type: 'PHASE_CHANGE',
            phase: (data.phase as AgentPhase) || 'idle',
            label: (data.label as string) || '',
          });
          trackStreamEvent({
            event: 'phase_changed',
            phase: (data.phase as AgentPhase) || 'idle',
            label: (data.label as string) || '',
            messageId: envelope.message_id,
          });
          break;

        case 'thought':
        case 'reasoning':
          // thought/reasoning events go to reasoning buffer
          const content = (data.delta as string) || (data.content as string) || '';
          if (content) {
            bufferedDispatch({ type: 'REASONING_CHUNK', delta: content });
          }
          break;

        case 'message':
          // message events go to content buffer (use delta field for streaming)
          const msgContent = (data.delta as string) || (data.content as string) || '';
          console.debug('[useChatStream] message event, delta:', msgContent.substring(0, 50));
          if (msgContent) {
            bufferedDispatch({ type: 'MESSAGE_CHUNK', delta: msgContent });
          }
          break;

        case 'tool_call':
          bufferedDispatch({
            type: 'TOOL_CALL',
            id: (data.id as string) || (data.tool_call_id as string) || `tc-${Date.now()}`,
            tool: (data.tool as string) || (data.tool_name as string) || 'unknown',
            label: (data.label as string) || (data.display_name as string) || (data.tool_name as string) || 'Tool',
          });
          trackStreamEvent({
            event: 'tool_call_seen',
            tool: (data.tool as string) || (data.tool_name as string) || 'unknown',
            messageId: envelope.message_id,
          });
          break;

        case 'tool_result':
          bufferedDispatch({
            type: 'TOOL_RESULT',
            id: (data.id as string) || (data.tool_call_id as string) || '',
            status: (data.status as string) || 'success',
            summary: (data.summary as string) || undefined,
          });
          break;

        case 'routing_decision':
          // Routing decision - just log, no state change needed
          console.debug('[useChatStream] Routing decision:', data);
          break;

        case 'citation':
          const citationData = data as unknown as CitationItem;
          if (citationData && citationData.paper_id) {
            bufferedDispatch({ type: 'CITATION', citation: citationData });
          }
          break;

        case 'confirmation_required':
          bufferedDispatch({
            type: 'CONFIRMATION_REQUIRED',
            confirmation: {
              confirmation_id: (data.confirmation_id as string) || '',
              tool: (data.tool_name as string) || 'unknown',
              params: (data.parameters as Record<string, unknown>) || {},
            },
          });
          trackStreamEvent({
            event: 'confirmation_required',
            tool: (data.tool_name as string) || 'unknown',
            messageId: envelope.message_id,
          });
          break;

        case 'done':
          bufferedDispatch({
            type: 'STREAM_COMPLETE',
            tokensUsed: (data.tokens_used as number) || 0,
            cost: (data.cost as number) || 0,
            durationMs: (data.total_time_ms as number) || (data.total_duration as number) || 0,
          });
          trackStreamEvent({
            event: 'stream_completed',
            tokensUsed: (data.tokens_used as number) || 0,
            durationMs: (data.total_time_ms as number) || (data.total_duration as number) || 0,
            messageId: envelope.message_id,
          });
          break;

        case 'error':
          bufferedDispatch({
            type: 'ERROR',
            code: (data.code as string) || 'UNKNOWN',
            message: (data.message as string) || (data.error as string) || 'Stream error',
          });
          trackStreamEvent({
            event: 'stream_error',
            code: (data.code as string) || 'UNKNOWN',
            messageId: envelope.message_id,
          });
          break;

        case 'heartbeat':
          // Ignore heartbeat events
          break;

        default:
          console.warn(`[useChatStream] Unknown event type: ${eventType}`);
      }
    },
    [bufferedDispatch]
  );

  // ============================================================================
  // Control Functions
  // ============================================================================

  /**
   * Start streaming session
   */
  const startStream = useCallback(
    (sessionId: string, taskType: TaskType, messageId: string) => {
      // Reset state first
      dispatch({ type: 'RESET' });

      // Set message ID for validation
      messageIdRef.current = messageId;

      // Clear buffers
      reasoningRef.current = '';
      contentRef.current = '';

      // Dispatch session start
      bufferedDispatch({
        type: 'SESSION_START',
        sessionId,
        taskType,
        messageId,
      });
    },
    [bufferedDispatch]
  );

  /**
   * Cancel current stream
   */
  const cancelStream = useCallback(
    (reason: string = 'User cancelled') => {
      forceFlush();
      bufferedDispatch({ type: 'CANCEL', reason });
      trackStreamEvent({ event: 'stream_cancelled', reason, messageId: messageIdRef.current });
    },
    [forceFlush, bufferedDispatch]
  );

  /**
   * Reset to initial state
   */
  const reset = useCallback(() => {
    forceFlush();
    dispatch({ type: 'RESET' });
    messageIdRef.current = '';
    reasoningRef.current = '';
    contentRef.current = '';
  }, [forceFlush]);

  // ============================================================================
  // Cleanup on Unmount
  // ============================================================================

  useEffect(() => {
    return () => {
      // HARD RULE 0.4: Force flush on unmount
      forceFlush();

      // Clear any pending timers
      if (throttleTimerRef.current) {
        clearTimeout(throttleTimerRef.current);
      }
    };
  }, [forceFlush]);

  // ============================================================================
  // Callback for onComplete
  // ============================================================================

  // Call onComplete when stream completes
  useEffect(() => {
    if (state.streamStatus === 'completed' && onComplete) {
      onComplete(state);
    }
  }, [state.streamStatus, state, onComplete]);

  // ============================================================================
  // Get buffered content (may be ahead of state due to throttle)
  // ============================================================================

  const getBufferedContent = useCallback(() => ({
    content: state.contentBuffer + contentRef.current,
    reasoning: state.reasoningBuffer + reasoningRef.current,
  }), [state.contentBuffer, state.reasoningBuffer]);

  // Reset confirmation state
  const resetConfirmation = useCallback(() => {
    dispatch({ type: 'CONFIRMATION_RESET' });
  }, [dispatch]);

  // ============================================================================
  // Return
  // ============================================================================

  return {
    state,
    dispatch: bufferedDispatch,
    startStream,
    handleSSEEvent,
    cancelStream,
    reset,
    forceFlush,
    currentMessageId: messageIdRef.current,
    getBufferedContent,
    confirmation: state.confirmation,
    resetConfirmation,
  };
}

