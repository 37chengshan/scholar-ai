import { useCallback, type MouseEvent, type MutableRefObject } from 'react';
import { toast } from 'sonner';
import type { ChatSession } from '@/app/hooks/useSessions';
import type { SSEService } from '@/services/sseService';

interface UseChatSessionControllerOptions {
  isZh: boolean;
  sessionToDelete: string | null;
  createSession: (title?: string) => Promise<ChatSession | null>;
  switchSession: (sessionId: string) => Promise<void>;
  deleteSession: (sessionId: string) => Promise<boolean>;
  resetForSessionSwitch: () => void;
  resetRuntimeRun: () => void;
  resetStreamingRun: () => void;
  openDeleteConfirm: (sessionId: string) => void;
  closeDeleteConfirm: () => void;
  setSessionSearchQuery: (value: string) => void;
  setSessionTokens: (value: number) => void;
  setSessionCost: (value: number) => void;
  sendLockRef: MutableRefObject<boolean>;
  sseServiceRef: MutableRefObject<SSEService | null>;
}

export function useChatSessionController({
  isZh,
  sessionToDelete,
  createSession,
  switchSession,
  deleteSession,
  resetForSessionSwitch,
  resetRuntimeRun,
  resetStreamingRun,
  openDeleteConfirm,
  closeDeleteConfirm,
  setSessionSearchQuery,
  setSessionTokens,
  setSessionCost,
  sendLockRef,
  sseServiceRef,
}: UseChatSessionControllerOptions) {
  const resetSessionState = useCallback(() => {
    sseServiceRef.current?.disconnect();
    sendLockRef.current = false;
    resetForSessionSwitch();
    setSessionTokens(0);
    setSessionCost(0);
    resetRuntimeRun();
    resetStreamingRun();
  }, [
    resetForSessionSwitch,
    resetRuntimeRun,
    resetStreamingRun,
    sendLockRef,
    setSessionCost,
    setSessionTokens,
    sseServiceRef,
  ]);

  const handleNewSession = useCallback(async () => {
    sseServiceRef.current?.disconnect();
    sendLockRef.current = false;

    const session = await createSession(isZh ? '新对话' : 'New Chat');
    if (!session) {
      return;
    }

    setSessionSearchQuery('');
    resetForSessionSwitch();
    setSessionTokens(0);
    setSessionCost(0);
    resetRuntimeRun();
    resetStreamingRun();
  }, [
    createSession,
    isZh,
    resetForSessionSwitch,
    resetRuntimeRun,
    resetStreamingRun,
    sendLockRef,
    setSessionCost,
    setSessionSearchQuery,
    setSessionTokens,
    sseServiceRef,
  ]);

  const handleSwitchSession = useCallback(async (sessionId: string) => {
    resetSessionState();
    await switchSession(sessionId);
  }, [resetSessionState, switchSession]);

  const handleDeleteSession = useCallback((sessionId: string, event: MouseEvent) => {
    event.stopPropagation();
    openDeleteConfirm(sessionId);
  }, [openDeleteConfirm]);

  const confirmDeleteSession = useCallback(async () => {
    if (!sessionToDelete) {
      return;
    }

    try {
      const deleted = await deleteSession(sessionToDelete);
      if (!deleted) {
        toast.error(isZh ? '删除失败' : 'Delete failed');
      } else {
        toast.success(isZh ? '对话已删除' : 'Session deleted');
      }
    } catch {
      toast.error(isZh ? '删除失败' : 'Delete failed');
    }

    closeDeleteConfirm();
  }, [closeDeleteConfirm, deleteSession, isZh, sessionToDelete]);

  const cancelDeleteSession = useCallback(() => {
    closeDeleteConfirm();
  }, [closeDeleteConfirm]);

  return {
    handleNewSession,
    handleSwitchSession,
    handleDeleteSession,
    confirmDeleteSession,
    cancelDeleteSession,
  };
}