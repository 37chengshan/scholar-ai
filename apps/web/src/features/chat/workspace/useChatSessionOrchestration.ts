import { useEffect } from 'react';
import { toast } from 'sonner';

import type { SSEService } from '@/services/sseService';
import type { SessionScopeMetadata } from '@/services/sessionsApi';
import { kbApi } from '@/services/kbApi';
import { applyScopeMetadataToSearchParams } from '@/features/chat/hooks/chatScopeQuery';
import { shouldPreserveComposerDraftForHandoff } from '@/features/chat/chatHandoff';
import { useChatSessionController } from '@/features/chat/hooks/useChatSessionController';

interface SessionLike {
  id: string;
  metadata?: unknown;
  updatedAt?: string;
  createdAt: string;
}

interface UseChatSessionOrchestrationParams {
  isZh: boolean;
  sessionToDelete: string | null;
  switchSession: (id: string) => Promise<void>;
  deleteSession: (id: string) => Promise<boolean>;
  resetForSessionSwitch: () => void;
  resetRuntimeRun: () => void;
  resetStreamingRun: () => void;
  closeDeleteConfirm: () => void;
  setSessionTokens: (tokens: number) => void;
  setSessionCost: (cost: number) => void;
  sendLockRef: React.MutableRefObject<boolean>;
  sseServiceRef: React.MutableRefObject<SSEService | null>;
  wantsNewSession: boolean;
  desiredSessionId: string | null;
  currentSession: SessionLike | null;
  searchParams: URLSearchParams;
  setSearchParams: (searchParams: URLSearchParams, options?: { replace?: boolean }) => void;
  clearCurrentSession: () => void;
  setInput: (value: string) => void;
  hasHandoffScopeWithoutSession: boolean;
  hasExplicitScopeInUrl: boolean;
  loading: boolean;
  safeSessions: SessionLike[];
  renderMessagesCount: number;
  sending: boolean;
  streamStatus: string;
  handledNewChatRef: React.MutableRefObject<boolean>;
  setForceNewSessionForNextSend: (value: boolean) => void;
}

export function useChatSessionOrchestration({
  isZh,
  sessionToDelete,
  switchSession,
  deleteSession,
  resetForSessionSwitch,
  resetRuntimeRun,
  resetStreamingRun,
  closeDeleteConfirm,
  setSessionTokens,
  setSessionCost,
  sendLockRef,
  sseServiceRef,
  wantsNewSession,
  desiredSessionId,
  currentSession,
  searchParams,
  setSearchParams,
  clearCurrentSession,
  setInput,
  hasHandoffScopeWithoutSession,
  hasExplicitScopeInUrl,
  loading,
  safeSessions,
  renderMessagesCount,
  sending,
  streamStatus,
  handledNewChatRef,
  setForceNewSessionForNextSend,
}: UseChatSessionOrchestrationParams) {
  const t = {
    terminal: isZh ? '终端对话' : 'Terminal',
    sessions: isZh ? '会话列表' : 'Sessions',
    search: isZh ? '搜索...' : 'Search...',
    history: isZh ? '历史记录' : 'History',
    newChat: isZh ? '新对话' : 'New Chat',
    placeholder: isZh ? '给 ScholarAI 发送消息...' : 'Message ScholarAI...',
    verify: isZh ? '请验证输出结果。' : 'Verify outputs.',
    noMessages: isZh ? '开始新对话' : 'Start a new conversation',
    sendFirst: isZh ? '发送您的第一条消息' : 'Send your first message',
    streaming: isZh ? '流式响应中...' : 'Streaming...',
    deleteConfirm: isZh ? '确定删除此对话？' : 'Delete this conversation?',
    stop: isZh ? '停止' : 'Stop',
    thinking: isZh ? '思考中...' : 'Thinking...',
  };

  const {
    handleSwitchSession,
    confirmDeleteSession,
    cancelDeleteSession,
  } = useChatSessionController({
    isZh,
    sessionToDelete,
    switchSession,
    deleteSession,
    resetForSessionSwitch,
    resetRuntimeRun,
    resetStreamingRun,
    closeDeleteConfirm,
    setSessionTokens,
    setSessionCost,
    sendLockRef,
    sseServiceRef,
  });

  useEffect(() => {
    if (!wantsNewSession) {
      handledNewChatRef.current = false;
      return;
    }

    if (handledNewChatRef.current) {
      return;
    }
    handledNewChatRef.current = true;

    setForceNewSessionForNextSend(true);

    sseServiceRef.current?.disconnect();
    sendLockRef.current = false;
    clearCurrentSession();
    resetForSessionSwitch();
    resetRuntimeRun();
    resetStreamingRun();
    setSessionTokens(0);
    setSessionCost(0);
    if (!shouldPreserveComposerDraftForHandoff(searchParams.toString())) {
      setInput('');
    }

    const next = new URLSearchParams(searchParams);
    next.delete('new');
    next.delete('session');
    setSearchParams(next, { replace: true });
  }, [
    clearCurrentSession,
    handledNewChatRef,
    resetForSessionSwitch,
    resetRuntimeRun,
    resetStreamingRun,
    searchParams,
    sendLockRef,
    setForceNewSessionForNextSend,
    setInput,
    setSearchParams,
    setSessionCost,
    setSessionTokens,
    sseServiceRef,
    wantsNewSession,
  ]);

  useEffect(() => {
    if (desiredSessionId) {
      setForceNewSessionForNextSend(false);
    }
  }, [desiredSessionId, setForceNewSessionForNextSend]);

  useEffect(() => {
    if (!desiredSessionId || !currentSession || currentSession.id !== desiredSessionId) {
      return;
    }

    const next = applyScopeMetadataToSearchParams(
      searchParams,
      (currentSession.metadata as Record<string, unknown> | null) ?? undefined,
    );
    next.set('session', desiredSessionId);
    next.delete('new');

    if (next.toString() === searchParams.toString()) {
      return;
    }

    setSearchParams(next, { replace: true });
  }, [currentSession, desiredSessionId, searchParams, setSearchParams]);

  useEffect(() => {
    if (!desiredSessionId || loading) {
      return;
    }

    if (currentSession?.id === desiredSessionId) {
      return;
    }

    if (!safeSessions.some((session) => session.id === desiredSessionId)) {
      return;
    }

    void handleSwitchSession(desiredSessionId);
  }, [currentSession?.id, desiredSessionId, handleSwitchSession, loading, safeSessions]);

  useEffect(() => {
    if (!desiredSessionId || loading) {
      return;
    }

    const targetSession = safeSessions.find((session) => session.id === desiredSessionId);
    const metadata = targetSession?.metadata as SessionScopeMetadata | null | undefined;
    if (!targetSession || metadata?.scopeType !== 'full_kb' || !metadata.kbId) {
      return;
    }
    const kbId = metadata.kbId;
    const sessionUpdatedAt = targetSession.updatedAt || targetSession.createdAt;

    let cancelled = false;

    const validateKnowledgeBaseSession = async () => {
      try {
        const knowledgeBase = await kbApi.get(kbId);
        if (cancelled) {
          return;
        }

        const staleByUpdatedAt =
          Boolean(metadata.kbUpdatedAt)
          && Boolean(knowledgeBase.updatedAt)
          && metadata.kbUpdatedAt !== knowledgeBase.updatedAt;
        const staleByPaperCount =
          typeof metadata.kbPaperCount === 'number'
          && metadata.kbPaperCount !== knowledgeBase.paperCount;
        const staleByChunkCount =
          typeof metadata.kbChunkCount === 'number'
          && metadata.kbChunkCount !== knowledgeBase.chunkCount;
        const hasKnowledgeBaseSnapshot =
          Boolean(metadata.kbUpdatedAt)
          || typeof metadata.kbPaperCount === 'number'
          || typeof metadata.kbChunkCount === 'number';
        const staleLegacySession =
          !hasKnowledgeBaseSnapshot
          && Boolean(sessionUpdatedAt)
          && Boolean(knowledgeBase.updatedAt)
          && new Date(knowledgeBase.updatedAt).getTime() > new Date(sessionUpdatedAt).getTime();

        if (!(staleByUpdatedAt || staleByPaperCount || staleByChunkCount || staleLegacySession)) {
          return;
        }

        toast.info(
          isZh
            ? '知识库内容已变化，已切换为新的知识库对话以避免沿用旧证据上下文'
            : 'Knowledge base changed. Starting a fresh KB chat to avoid stale evidence context.',
        );

        const next = new URLSearchParams(searchParams);
        next.delete('session');
        next.set('kbId', kbId);
        next.set('new', '1');
        setSearchParams(next, { replace: true });
      } catch {
        // Leave the existing session reachable if KB validation fails.
      }
    };

    void validateKnowledgeBaseSession();

    return () => {
      cancelled = true;
    };
  }, [desiredSessionId, isZh, loading, safeSessions, searchParams, setSearchParams]);

  useEffect(() => {
    if (
      wantsNewSession
      || desiredSessionId
      || hasHandoffScopeWithoutSession
      || (hasExplicitScopeInUrl && !desiredSessionId)
      || !currentSession?.id
    ) {
      return;
    }

    const conversationStarted = renderMessagesCount > 0 || sending || streamStatus === 'streaming';
    if (!conversationStarted) {
      return;
    }

    const next = new URLSearchParams(searchParams);
    next.set('session', currentSession.id);
    next.delete('new');

    if (next.toString() === searchParams.toString()) {
      return;
    }

    setSearchParams(next, { replace: true });
  }, [
    currentSession?.id,
    desiredSessionId,
    hasExplicitScopeInUrl,
    hasHandoffScopeWithoutSession,
    renderMessagesCount,
    searchParams,
    sending,
    setSearchParams,
    streamStatus,
    wantsNewSession,
  ]);

  return {
    t,
    confirmDeleteSession,
    cancelDeleteSession,
  };
}
