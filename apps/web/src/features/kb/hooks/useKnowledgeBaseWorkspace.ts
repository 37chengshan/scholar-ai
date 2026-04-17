import { useMemo } from 'react';
import { useSearchParams } from 'react-router';

export function useKnowledgeBaseWorkspace() {
  const [searchParams] = useSearchParams();

  const activeTab = useMemo(() => searchParams.get('tab') ?? 'papers', [searchParams]);

  return {
    activeTab,
  };
}
