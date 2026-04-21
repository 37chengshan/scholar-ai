import { useCallback, useEffect, useRef, type MutableRefObject } from 'react';
import { toast } from 'sonner';
import { API_BASE_URL } from '@/config/api';
import { SSEService, type SSEEventEnvelope } from '@/services/sseService';
import type { AgentRun, PendingAction, RunStatus } from '@/features/chat/types/run';
import type { UseRuntimeReturn } from '@/features/chat/runtime/useRuntime';
import type { ChatStreamState, SSEAction } from '@/app/hooks/useChatStream';

type RuntimeState = Pick<UseRuntimeReturn, 'run' | 'ingestEvent' | 'dispatchRun'>;

type StreamStateSnapshot = Pick<
  ChatStreamState,
  'streamStatus' | 'tokensUsed' | 'cost' | 'startedAt' | 'endedAt'
>;

interface ConfirmationState {
  confirmation_id: string;
  tool?: string;
  params?: Record<string, unknown>;
}

interface UseChatRuntimeBridgeOptions {
  isZh: boolean;
  currentSessionId: string | null;
  currentMessageId: string | null;
  currentMessageIdRef: MutableRefObject<string>;
  sseServiceRef: MutableRefObject<SSEService | null>;
  runtime: RuntimeState;
  streamState: StreamStateSnapshot;
  confirmation: ConfirmationState | null;
  resetConfirmation: () => void;
  handleSSEEvent: (event: {
    message_id: string;
    event_type: string;
    data: unknown;
    timestamp: number;
  }) => void;
  dispatch: (action: SSEAction) => void;
  syncStreamingMessage: (messageId: string) => void;
  setActiveRun: (run: AgentRun) => void;
  setSelectedRunId: (runId: string | null) => void;
  setActiveRunStatus: (status: RunStatus) => void;
  setPendingActions: (actions: PendingAction[]) => void;
  setRecoveryBannerVisible: (visible: boolean) => void;
  setRunArtifactsPanelOpen: (open: boolean) => void;
  setStreamingMessageId: (messageId: string | null) => void;
}

export function useChatRuntimeBridge({
  isZh,
  currentSessionId,
  currentMessageId,
  currentMessageIdRef,
  sseServiceRef,
  runtime,
  streamState,
  confirmation,
  resetConfirmation,
  handleSSEEvent,
  dispatch,
  syncStreamingMessage,
  setActiveRun,
  setSelectedRunId,
  setActiveRunStatus,
  setPendingActions,
  setRecoveryBannerVisible,
  setRunArtifactsPanelOpen,
  setStreamingMessageId,
}: UseChatRuntimeBridgeOptions) {
  const streamStateRef = useRef(streamState);

  useEffect(() => {
    streamStateRef.current = streamState;
  }, [streamState]);

  const ingestRuntimeEvent = useCallback((event: SSEEventEnvelope) => {
    runtime.ingestEvent({
      message_id: event.message_id || currentMessageIdRef.current,
      event: event.event || '',
      data: event.data ?? {},
      timestamp: Date.now(),
    });
  }, [currentMessageIdRef, runtime]);

  useEffect(() => {
    setActiveRun(runtime.run);
    setSelectedRunId(runtime.run.runId);
    setActiveRunStatus(runtime.run.status);
    setPendingActions(runtime.run.pendingActions);
    setRecoveryBannerVisible(runtime.run.recoverable || runtime.run.pendingActions.length > 0);
    setRunArtifactsPanelOpen(runtime.run.artifacts.length > 0 || runtime.run.evidence.length > 0);
  }, [
    runtime.run,
    setActiveRun,
    setSelectedRunId,
    setActiveRunStatus,
    setPendingActions,
    setRecoveryBannerVisible,
    setRunArtifactsPanelOpen,
  ]);

  useEffect(() => {
    if (streamState.streamStatus === 'cancelled' && runtime.run.status === 'running') {
      runtime.dispatchRun({
        type: 'RUN_COMPLETE',
        status: 'cancelled',
        tokensUsed: streamState.tokensUsed,
        cost: streamState.cost,
      });
      return;
    }

    if (streamState.streamStatus === 'error' && runtime.run.status === 'running') {
      runtime.dispatchRun({
        type: 'RUN_COMPLETE',
        status: 'failed',
        tokensUsed: streamState.tokensUsed,
        cost: streamState.cost,
      });
    }
  }, [runtime, streamState.cost, streamState.streamStatus, streamState.tokensUsed]);

  useEffect(() => {
    setStreamingMessageId(currentMessageId);
  }, [currentMessageId, setStreamingMessageId]);

  const handleConfirmation = useCallback(async (approved: boolean) => {
    if (!confirmation) {
      return;
    }

    try {
      if (!sseServiceRef.current) {
        sseServiceRef.current = new SSEService();
      }

      sseServiceRef.current.connect(`${API_BASE_URL}/api/v1/chat/confirm`, {
        onEnvelope: (event: SSEEventEnvelope) => {
          const eventMessageId = event.message_id || '';
          const nextMessageId = currentMessageIdRef.current || eventMessageId;

          handleSSEEvent({
            message_id: eventMessageId,
            event_type: event.event || '',
            data: event.data,
            timestamp: Date.now(),
          });
          ingestRuntimeEvent(event);
          syncStreamingMessage(nextMessageId);
        },
        onError: (error) => {
          dispatch({
            type: 'ERROR',
            code: 'STREAM_ERROR',
            message: error.message,
          });
          toast.error(isZh ? '确认后恢复失败' : 'Failed to resume after confirmation');
        },
        onDone: () => {
          dispatch({
            type: 'STREAM_COMPLETE',
            tokensUsed: streamStateRef.current.tokensUsed,
            cost: streamStateRef.current.cost,
            durationMs:
              streamStateRef.current.endedAt && streamStateRef.current.startedAt
                ? streamStateRef.current.endedAt - streamStateRef.current.startedAt
                : 0,
          });
        },
      }, {
        confirmation_id: confirmation.confirmation_id,
        approved,
        session_id: currentSessionId || '',
      });

      resetConfirmation();
    } catch {
      toast.error(approved ? (isZh ? '批准失败' : 'Approval failed') : (isZh ? '拒绝失败' : 'Rejection failed'));
      resetConfirmation();
    }
  }, [
    confirmation,
    currentMessageIdRef,
    currentSessionId,
    dispatch,
    handleSSEEvent,
    ingestRuntimeEvent,
    isZh,
    resetConfirmation,
    sseServiceRef,
    syncStreamingMessage,
  ]);

  return {
    ingestRuntimeEvent,
    handleConfirmation,
  };
}