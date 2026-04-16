import { useMemo } from 'react';
import { useSearchParams } from 'react-router';

export function useChatWorkspace() {
  const [searchParams] = useSearchParams();

  const scope = useMemo(() => ({
    paperId: searchParams.get('paperId'),
    kbId: searchParams.get('kbId'),
  }), [searchParams]);

  return {
    scope,
  };
}
