import { useCallback, useMemo, useState } from 'react';
import {
  useChatStream,
  type TaskType,
  type UseChatStreamOptions,
} from '@/app/hooks/useChatStream';

export function useChatStreaming(options: UseChatStreamOptions = {}) {
  const [currentMessageId, setCurrentMessageId] = useState<string | null>(null);

  const {
    state,
    dispatch,
    startStream,
    handleSSEEvent,
    cancelStream,
    reset,
    forceFlush,
    getBufferedContent,
    confirmation,
    resetConfirmation,
  } = useChatStream(options);

  const startRun = useCallback((sessionId: string, taskType: TaskType, messageId: string) => {
    setCurrentMessageId(messageId);
    startStream(sessionId, taskType, messageId);
  }, [startStream]);

  const stopRun = useCallback((reason = 'User stopped') => {
    cancelStream(reason);
    setCurrentMessageId(null);
  }, [cancelStream]);

  const resetRun = useCallback(() => {
    reset();
    setCurrentMessageId(null);
  }, [reset]);

  return useMemo(() => ({
    streamState: state,
    dispatch,
    startRun,
    stopRun,
    resetRun,
    handleSSEEvent,
    forceFlush,
    getBufferedContent,
    currentMessageId,
    setCurrentMessageId,
    confirmation,
    resetConfirmation,
  }), [
    state,
    dispatch,
    startRun,
    stopRun,
    resetRun,
    handleSSEEvent,
    forceFlush,
    getBufferedContent,
    currentMessageId,
    setCurrentMessageId,
    confirmation,
    resetConfirmation,
  ]);
}
