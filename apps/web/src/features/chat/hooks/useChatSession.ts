import { useMemo } from 'react';
import { useSessions } from '@/app/hooks/useSessions';

export function useChatSession() {
  const sessionsApi = useSessions();

  return useMemo(() => sessionsApi, [sessionsApi]);
}
