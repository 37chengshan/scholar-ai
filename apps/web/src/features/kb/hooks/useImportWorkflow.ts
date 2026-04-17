import { useCallback } from 'react';

interface ImportWorkflowActions {
  onImportComplete: () => Promise<void> | void;
  onImportRetry?: () => Promise<void> | void;
  onImportCancel?: () => Promise<void> | void;
}

export function useImportWorkflow(actions: ImportWorkflowActions) {
  const { onImportComplete, onImportRetry, onImportCancel } = actions;

  const handleImportCompleted = useCallback(async () => {
    await onImportComplete();
  }, [onImportComplete]);

  const handleImportRetry = useCallback(async () => {
    if (onImportRetry) {
      await onImportRetry();
      return;
    }
    await onImportComplete();
  }, [onImportComplete, onImportRetry]);

  const handleImportCancel = useCallback(async () => {
    if (onImportCancel) {
      await onImportCancel();
      return;
    }
    await onImportComplete();
  }, [onImportCancel, onImportComplete]);

  return {
    handleImportCompleted,
    handleImportRetry,
    handleImportCancel,
  };
}
