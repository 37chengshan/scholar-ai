/**
 * useSSE Hook - SSE Connection Management for React Components
 *
 * Provides React integration for SSEService with:
 * - Connection state management (isConnected, messages, error)
 * - Automatic cleanup on unmount
 * - Message accumulation for streaming responses
 *
 * Usage:
 * ```tsx
 * function ChatComponent() {
 *   const { isConnected, messages, error, connect, disconnect } = useSSE();
 *
 *   const handleSend = () => {
 *     connect('/api/chat/stream?message=hello');
 *   };
 *
 *   useEffect(() => {
 *     messages.forEach(msg => {
 *       if (msg.type === 'message') {
 *         console.log('AI response:', msg.content);
 *       }
 *     });
 *   }, [messages]);
 *
 *   return <div>...</div>;
 * }
 * ```
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { sseService, SSEEvent } from '@/services/sseService';
import { ToolCall, PaperCitation, TokenUsage } from '@/types/chat';

/**
 * Confirmation request from agent (Sprint 3: Added confirmation_id)
 */
interface ConfirmationState {
  confirmation_id: string;  // Required for backend resumption
  tool: string;
  params: Record<string, unknown>;
}

/**
 * Hook return type
 */
interface UseSSEReturn {
  /** Whether SSE connection is active */
  isConnected: boolean;
  /** All received messages since connect() was called */
  messages: SSEEvent[];
  /** Error message if connection failed */
  error: string | null;
  /** Accumulated message content (for streaming text) */
  accumulatedContent: string;
  /** Token usage from last request */
  tokensUsed: number;
  /** Cost from last request */
  cost: number;
  /** Total execution time in ms */
  totalTimeMs: number;
  /** Structured tool calls array */
  toolCalls: ToolCall[];
  /** Confirmation request from agent */
  confirmation: ConfirmationState | null;
  /** Extracted citations */
  citations: PaperCitation[];
  /** Token usage for current message */
  currentMessageTokens: TokenUsage | null;
  /** Connect to SSE endpoint with POST body */
  connect: (url: string, body?: Record<string, unknown>) => void;
  /** Disconnect from SSE endpoint */
  disconnect: () => void;
  /** Clear all messages */
  clearMessages: () => void;
  /** Reset confirmation state */
  resetConfirmation: () => void;
}

/**
 * useSSE Hook
 *
 * Manages SSE connection lifecycle in React components.
 * Automatically disconnects on component unmount.
 *
 * @returns SSE state and control functions
 */
export function useSSE(): UseSSEReturn {
  // Connection state
  const [isConnected, setIsConnected] = useState(false);
  const [messages, setMessages] = useState<SSEEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [tokensUsed, setTokensUsed] = useState(0);
  const [cost, setCost] = useState(0);
  const [totalTimeMs, setTotalTimeMs] = useState(0);

  // Structured tool event state (new for Phase 28-03)
  const [toolCalls, setToolCalls] = useState<ToolCall[]>([]);
  const [confirmation, setConfirmation] = useState<ConfirmationState | null>(null);
  const [citations, setCitations] = useState<PaperCitation[]>([]);
  const [currentMessageTokens, setCurrentMessageTokens] = useState<TokenUsage | null>(null);

  // Ref for accumulated content (avoids stale closure issues)
  const accumulatedContent = useRef<string>('');
  // Ref for tool call tracking (avoids stale closure in event handler)
  const toolCallsRef = useRef<ToolCall[]>([]);

  /**
   * Connect to SSE endpoint using POST
   *
   * @param url - SSE endpoint URL
   * @param body - POST body (message, session_id, etc.)
   */
  const connect = useCallback((url: string, body?: Record<string, unknown>) => {
    // Reset state
    setIsConnected(true);
    setError(null);
    setMessages([]);
    setTokensUsed(0);
    setCost(0);
    setTotalTimeMs(0);
    accumulatedContent.current = '';

    // Reset tool-specific state
    setToolCalls([]);
    toolCallsRef.current = [];
    setConfirmation(null);
    setCitations([]);
    setCurrentMessageTokens(null);

    sseService.connect(url, {
      onMessage: (event: SSEEvent) => {
        // Add message to list
        setMessages((prev) => [...prev, event]);

        // Accumulate message content for streaming text
        // Use event.content for actual content (not event.type which is SSE event type)
        if (event.type === 'message' && typeof event.content.content === 'string') {
          accumulatedContent.current += event.content.content;
        }

        // Handle tool_call events - extract from event.content
        if (event.type === 'tool_call') {
          const toolCall: ToolCall = {
            id: `tc-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
            tool: event.content.tool || event.tool || 'unknown',
            parameters: event.content.parameters || {},
            status: 'running',
            startedAt: Date.now(),
          };
          toolCallsRef.current = [...toolCallsRef.current, toolCall];
          setToolCalls(toolCallsRef.current);
        }

        // Handle tool_result events - extract from event.content
        if (event.type === 'tool_result') {
          const toolName = event.content.tool || event.tool || 'unknown';
          const toolCallsCopy = [...toolCallsRef.current];
          for (let i = toolCallsCopy.length - 1; i >= 0; i--) {
            const tc = toolCallsCopy[i];
            if (tc.tool === toolName && tc.status === 'running') {
              tc.status = event.content.success !== false ? 'success' : 'error';
              tc.result = event.content.data ?? event.content.result ?? event.result;
              tc.completedAt = Date.now();
              tc.duration = tc.completedAt - tc.startedAt;
              break;
            }
          }
          toolCallsRef.current = toolCallsCopy;
          setToolCalls(toolCallsCopy);
        }

        // Handle confirmation_required events - extract from event.content (Sprint 3: Add confirmation_id)
        if (event.type === 'confirmation_required') {
          setConfirmation({
            confirmation_id: event.content.confirmation_id || '',  // Required for backend resumption
            tool: event.content.tool_name || event.content.tool || 'unknown',
            params: event.content.parameters || event.content.params || {},
          });
        }

        // Handle citation events - extract from event.content
        if (event.type === 'citation') {
          const citationData = event.content || event.data;
          if (citationData && Array.isArray(citationData)) {
            const citations: PaperCitation[] = citationData.map((c: any) => ({
              paper_id: c.paper_id || c.id || '',
              title: c.title || 'Unknown',
              authors: c.authors || [],
              year: c.year || 0,
              journal: c.journal,
              page: c.page || 0,
              snippet: c.snippet || c.content || '',
              score: c.score || c.relevance || 0,
              content_type: c.content_type || 'text',
              chunk_id: c.chunk_id,
            }));
            setCitations(citations);
          }
        }
      },
      onError: (err: Error) => {
        setError(err.message);
        setIsConnected(false);
      },
      onDone: (data) => {
        setIsConnected(false);
        if (data) {
          setTokensUsed(data.tokens_used || 0);
          setCost(data.cost || 0);
          setTotalTimeMs(data.total_time_ms || 0);

          setCurrentMessageTokens({
            tokensUsed: data.tokens_used || 0,
            cost: data.cost || 0,
          });

          if (data.citations && Array.isArray(data.citations)) {
            const citations: PaperCitation[] = data.citations.map((c: any) => ({
              paper_id: c.paper_id || c.id || '',
              title: c.title || 'Unknown',
              authors: c.authors || [],
              year: c.year || 0,
              journal: c.journal,
              page: c.page || 0,
              snippet: c.snippet || c.content || '',
              score: c.score || c.relevance || 0,
              content_type: c.content_type || 'text',
              chunk_id: c.chunk_id,
            }));
            setCitations(citations);
          }
        }
      },
    }, body);
  }, []);

  /**
   * Disconnect from SSE endpoint
   */
  const disconnect = useCallback(() => {
    sseService.disconnect();
    setIsConnected(false);
  }, []);

  /**
   * Clear all messages
   */
  const clearMessages = useCallback(() => {
    setMessages([]);
    accumulatedContent.current = '';
  }, []);

  /**
   * Reset confirmation state (new for Phase 28-03)
   */
  const resetConfirmation = useCallback(() => {
    setConfirmation(null);
  }, []);

  /**
   * Cleanup on unmount
   */
  useEffect(() => {
    return () => {
      sseService.disconnect();
    };
  }, []);

  return {
    isConnected,
    messages,
    error,
    accumulatedContent: accumulatedContent.current,
    tokensUsed,
    cost,
    totalTimeMs,
    // New for Phase 28-03
    toolCalls,
    confirmation,
    citations,
    currentMessageTokens,
    connect,
    disconnect,
    clearMessages,
    resetConfirmation,
  };
}

export type { UseSSEReturn };