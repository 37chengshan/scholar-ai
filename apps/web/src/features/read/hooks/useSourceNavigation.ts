import { useMemo } from 'react';
import { useSearchParams } from 'react-router';

export function useSourceNavigation() {
  const [params] = useSearchParams();

  return useMemo(() => ({
    source: params.get('source') || 'read',
    sourceId: params.get('source_id') || '',
    page: Number(params.get('page') || '1') || 1,
  }), [params]);
}
