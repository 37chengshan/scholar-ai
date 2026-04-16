import { useCallback } from 'react';

export function useImportWorkflow(onRefresh: () => Promise<void> | void) {
  const handleImportCompleted = useCallback(async () => {
    await onRefresh();
  }, [onRefresh]);

  return {
    handleImportCompleted,
  };
}
