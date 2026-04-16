import { useMemo } from 'react';
import { useChatStream } from '@/app/hooks/useChatStream';

export function useChatStreaming() {
  const stream = useChatStream();

  return useMemo(() => stream, [stream]);
}
