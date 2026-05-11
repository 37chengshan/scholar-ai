import { useCallback, useDeferredValue, useEffect, useMemo } from 'react';
import type { NavigateFunction } from 'react-router';
import type { ScopeType } from '@/app/components/ScopeBanner';
import type { ThinkingStep } from '@/app/components/ThinkingProcess';
import type { ChatStreamState } from '@/app/hooks/useChatStream';
import type { CitationItem } from '@/features/chat/components/workspaceTypes';
import { navigateToSafeTarget } from '@/lib/navigation';
import { toast } from 'sonner';

interface UseChatWorkspaceViewStateOptions {
  isZh: boolean;
  mode: 'auto' | 'rag' | 'agent';
  uiScope: {
    type: ScopeType | null;
  };
  streamState: ChatStreamState;
  runtimeRun: any;
  renderMessages: unknown[];
  maybeFollowBottom: (reason: 'stream' | 'message') => void;
  alignToBottom: () => void;
  navigate: NavigateFunction;
  onSend: () => void;
}

export function useChatWorkspaceViewState({
  isZh,
  mode,
  uiScope,
  streamState,
  runtimeRun,
  renderMessages,
  maybeFollowBottom,
  alignToBottom,
  navigate,
  onSend,
}: UseChatWorkspaceViewStateOptions) {
  useEffect(() => {
    const reason = streamState.streamStatus === 'streaming' ? 'stream' : 'message';
    maybeFollowBottom(reason);
  }, [renderMessages, streamState.contentBuffer, streamState.streamStatus, maybeFollowBottom]);

  useEffect(() => {
    if (
      streamState.streamStatus === 'completed'
      || streamState.streamStatus === 'cancelled'
      || streamState.streamStatus === 'error'
    ) {
      alignToBottom();
    }
  }, [alignToBottom, streamState.streamStatus]);

  const thinkingSteps = useMemo<ThinkingStep[]>(() => {
    if (!streamState.reasoningBuffer) {
      return [];
    }

    return streamState.reasoningBuffer
      .split('\n')
      .filter(Boolean)
      .map((line, idx) => ({
        type: 'thinking',
        content: line,
        timestamp: streamState.startedAt
          ? streamState.startedAt + idx * 100
          : undefined,
      }));
  }, [streamState.reasoningBuffer, streamState.startedAt]);

  const deferredRun = useDeferredValue(runtimeRun);

  const panelStreamState = useMemo(() => {
    if (streamState.streamStatus !== 'streaming') {
      return streamState;
    }

    return {
      ...streamState,
      contentBuffer: '',
      reasoningBuffer: '',
    };
  }, [streamState]);

  const handleKeyDown = useCallback((event: React.KeyboardEvent) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      onSend();
    }
  }, [onSend]);

  const handleCitationClick = useCallback((citation: CitationItem | undefined) => {
    if (!citation) {
      return;
    }

    if (!citation.paper_id) {
      toast.warning(isZh ? '引用缺少论文 ID，无法跳转' : 'Citation is missing paper id');
      return;
    }

    const page = citation.page_num || citation.page || 1;
    if (!citation.page_num && !citation.page) {
      toast.warning(isZh ? '引用缺少页码，已跳转到第一页' : 'Citation has no page; opening first page');
    }
    if (navigateToSafeTarget(citation.citation_jump_url, navigate)) {
      return;
    }

    const canonicalSourceId = citation.source_chunk_id || citation.source_id || citation.chunk_id || '';
    const sourceQuery = canonicalSourceId
      ? `&source=chat&source_id=${encodeURIComponent(canonicalSourceId)}`
      : '';
    navigate(`/read/${citation.paper_id}?page=${page}${sourceQuery}`);
  }, [isZh, navigate]);

  const scopeHint = useMemo(() => {
    const scopeLabel = uiScope.type === 'single_paper'
      ? (isZh ? '当前论文' : 'Current paper')
      : uiScope.type === 'full_kb'
        ? (isZh ? '当前知识库' : 'Current KB')
        : uiScope.type === 'compare'
          ? (isZh ? '当前对比集' : 'Current comparison set')
          : (isZh ? '全局' : 'Global');
    const modeLabel = mode === 'auto'
      ? (isZh ? '自动' : 'Auto')
      : mode === 'rag'
        ? (isZh ? '快速问答' : 'Fast RAG')
        : (isZh ? '深度分析' : 'Deep Agent');

    return `${isZh ? '范围' : 'Scope'}：${scopeLabel} · ${isZh ? '模式' : 'Mode'}：${modeLabel}`;
  }, [isZh, mode, uiScope.type]);

  const errorStage = useMemo(() => {
    if (streamState.streamStatus !== 'error') {
      return undefined;
    }

    const phase = runtimeRun?.phase || runtimeRun?.currentPhase || 'unknown';
    if (!isZh) {
      return phase;
    }
    if (phase === 'planning') return '规划';
    if (phase === 'executing') return '检索/执行';
    if (phase === 'verifying') return '验证';
    if (phase === 'failed') return '失败';
    return String(phase);
  }, [isZh, runtimeRun?.currentPhase, runtimeRun?.phase, streamState.streamStatus]);

  const formatTime = useCallback((dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleTimeString(isZh ? 'zh-CN' : 'en-US', {
      hour: '2-digit',
      minute: '2-digit',
    });
  }, [isZh]);

  return {
    thinkingSteps,
    deferredRun,
    panelStreamState,
    handleKeyDown,
    handleCitationClick,
    scopeHint,
    errorStage,
    formatTime,
  };
}
