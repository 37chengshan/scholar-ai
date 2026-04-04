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
  /** Connect to SSE endpoint */
  connect: (url: string) => void;
  /** Disconnect from SSE endpoint */
  disconnect: () => void;
  /** Clear all messages */
  clearMessages: () => void;
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

  // Ref for accumulated content (avoids stale closure issues)
  const accumulatedContent = useRef<string>('');

  /**
   * Connect to SSE endpoint
   *
   * @param url - SSE endpoint URL
   */
  const connect = useCallback((url: string) => {
    // Reset state
    setIsConnected(true);
    setError(null);
    setMessages([]);
    accumulatedContent.current = '';

    sseService.connect(url, {
      onMessage: (event: SSEEvent) => {
        // Add message to list
        setMessages((prev) => [...prev, event]);

        // Accumulate message content for streaming text
        if (event.type === 'message' && typeof event.content === 'string') {
          accumulatedContent.current += event.content;
        }
      },
      onError: (err: Error) => {
        setError(err.message);
        setIsConnected(false);
      },
      onDone: () => {
        setIsConnected(false);
      },
    });
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
    connect,
    disconnect,
    clearMessages,
  };
}

export type { UseSSEReturn };