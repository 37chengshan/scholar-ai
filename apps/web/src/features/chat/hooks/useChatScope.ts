import { useMemo } from 'react';
import { useSearchParams } from 'react-router';

interface ChatScopeState {
  paperId: string | null;
  kbId: string | null;
  scopeType: 'single_paper' | 'full_kb' | null;
  hasScopeError: boolean;
}

export function useChatScope(): ChatScopeState {
  const [searchParams] = useSearchParams();

  return useMemo(() => {
    const paperId = searchParams.get('paperId');
    const kbId = searchParams.get('kbId');
    const hasScopeError = Boolean(paperId && kbId);

    let scopeType: ChatScopeState['scopeType'] = null;
    if (!hasScopeError) {
      if (paperId) {
        scopeType = 'single_paper';
      } else if (kbId) {
        scopeType = 'full_kb';
      }
    }

    return {
      paperId,
      kbId,
      scopeType,
      hasScopeError,
    };
  }, [searchParams]);
}
