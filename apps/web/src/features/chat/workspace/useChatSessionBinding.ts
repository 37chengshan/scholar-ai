import { useMemo } from 'react';

import { useSessions } from '@/app/hooks/useSessions';

export function useChatSessionBinding(searchParams: URLSearchParams) {
  const desiredSessionId = searchParams.get('session');
  const wantsNewSession = searchParams.get('new') === '1';
  const hasExplicitScopeInUrl = Boolean(
    searchParams.get('paperId') || searchParams.get('kbId') || searchParams.get('paper_ids'),
  );
  const hasHandoffScopeWithoutSession = searchParams.get('handoff') === '1'
    && !desiredSessionId
    && hasExplicitScopeInUrl;
  const shouldSuppressSessionAutoSelect =
    wantsNewSession || hasHandoffScopeWithoutSession || (hasExplicitScopeInUrl && !desiredSessionId);
  const messageSessionId = hasExplicitScopeInUrl && !desiredSessionId
    ? null
    : desiredSessionId ?? undefined;

  const sessionsState = useSessions({
    autoSelectLatest: !shouldSuppressSessionAutoSelect,
    messageSessionId,
  });

  const safeSessions = useMemo(
    () => sessionsState.sessions.filter((session) => Boolean(session?.id)),
    [sessionsState.sessions],
  );

  return {
    ...sessionsState,
    desiredSessionId,
    wantsNewSession,
    hasExplicitScopeInUrl,
    hasHandoffScopeWithoutSession,
    safeSessions,
  };
}
