import { useMemo } from 'react';
import { useChatStream } from '@/app/hooks/useChatStream';

export function useChatStreaming() {
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
  } = useChatStream();

  return useMemo(() => ({
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
  }), [
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
  ]);
}
