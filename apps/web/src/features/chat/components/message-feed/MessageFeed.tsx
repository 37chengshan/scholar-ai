import { AlertCircle, Bot, Loader2, Square, User } from 'lucide-react';
import { clsx } from 'clsx';
import type { ChatStreamState } from '@/app/hooks/useChatStream';
import type { ThinkingStep } from '@/app/components/ThinkingProcess';
import { renderContentWithCitations } from '@/app/components/CitationsPanel';
import { UnifiedEmptyState, UnifiedErrorState } from '@/app/components/UnifiedFeedbackState';
import { ReasoningPanel } from '@/features/chat/components/reasoning-panel/ReasoningPanel';
import { ToolTimelinePanel } from '@/features/chat/components/tool-timeline/ToolTimelinePanel';
import { CitationPanel } from '@/features/chat/components/citation-panel/CitationPanel';
import type { CitationItem, ToolTimelineItem } from '@/features/chat/components/workspaceTypes';
import type { ChatRenderMessage } from '@/features/chat/hooks/useChatMessagesViewModel';

interface MessageFeedCopy {
  noMessages: string;
  sendFirst: string;
  thinking: string;
  stop: string;
}

interface MessageFeedProps {
  renderMessages: ChatRenderMessage[];
  streamState: ChatStreamState;
  currentMessageId: string;
  thinkingSteps: ThinkingStep[];
  labels: MessageFeedCopy;
  messagesEndRef: React.RefObject<HTMLDivElement>;
  scrollContainerRef?: React.RefObject<HTMLDivElement>;
  onCitationClick: (citation: CitationItem | undefined) => void;
  onStop: () => void;
  formatTime: (date: string) => string;
}

const safeToolTimeline = (timeline?: ToolTimelineItem[]) => (timeline || []).filter(Boolean);
const safeCitations = (citations?: CitationItem[]) => (citations || []).filter(Boolean);

function getReasoningVisible(
  isAssistant: boolean,
  messageReasoning?: string,
  streamReasoning?: string,
): boolean {
  return isAssistant && Boolean(messageReasoning || streamReasoning);
}

function getToolTimelineVisible(
  isAssistant: boolean,
  messageToolTimeline?: ToolTimelineItem[],
  streamToolTimeline?: ToolTimelineItem[],
): boolean {
  return isAssistant
    && (((messageToolTimeline?.length || 0) > 0) || ((streamToolTimeline?.length || 0) > 0));
}

export function MessageFeed({
  renderMessages,
  streamState,
  currentMessageId,
  thinkingSteps,
  labels,
  messagesEndRef,
  scrollContainerRef,
  onCitationClick,
  onStop,
  formatTime,
}: MessageFeedProps) {
  return (
    <div ref={scrollContainerRef} className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden px-4 sm:px-6 py-5">
      {renderMessages.length === 0 ? (
        <div className="mx-auto mt-12 max-w-2xl">
          <UnifiedEmptyState title={labels.noMessages} description={labels.sendFirst} />
        </div>
      ) : (
        <div className="mx-auto flex w-full flex-col gap-4">
          {renderMessages.map((message) => {
              const isStreaming = message.isStreaming;
              const isPlaceholder = message.isPlaceholder || message.id === currentMessageId;
              const isAssistant = message.role === 'assistant';
              const isActiveStreamMessage = isAssistant && isStreaming && isPlaceholder;
              const messageReasoning = isActiveStreamMessage
                ? (message.displayReasoning || streamState.reasoningBuffer)
                : (message.displayReasoning || '');
              const messageToolTimeline = isActiveStreamMessage
                ? safeToolTimeline(message.displayToolTimeline.length > 0 ? message.displayToolTimeline : streamState.toolTimeline)
                : safeToolTimeline(message.displayToolTimeline);
              const localCitations = safeCitations(message.displayCitations);
              const messageCitations = localCitations.length > 0
                ? localCitations
                : (isActiveStreamMessage ? safeCitations(streamState.citations) : []);
              const reasoningVisible = getReasoningVisible(isAssistant, messageReasoning, undefined);
              const toolTimelineVisible = getToolTimelineVisible(isAssistant, messageToolTimeline, undefined);
              const showStreamingMeta = isActiveStreamMessage && (reasoningVisible || toolTimelineVisible);
              const messageReasoningSteps = messageReasoning
                .split('\n')
                .filter(Boolean)
                .map((line) => ({ type: 'thinking' as const, content: line }));
              const tokenCount = message.tokensUsed;
              const costValue = message.cost ?? 0;

              return (
                <div
                  key={message.id}
                  className={clsx(
                    'flex items-start gap-3',
                    isAssistant ? 'justify-start' : 'justify-end',
                  )}
                >
                  {isAssistant && (
                    <div className="mt-1 flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full border border-primary/15 bg-primary/5 text-primary shadow-sm">
                      <Bot className="h-4 w-4" />
                    </div>
                  )}

                  <div
                    className={clsx(
                      'flex max-w-[min(44rem,100%)] flex-col gap-2',
                      isAssistant ? 'items-start' : 'items-end',
                    )}
                  >
                    <ReasoningPanel
                      visible={reasoningVisible && !isStreaming}
                      steps={messageReasoningSteps.length > 0 ? messageReasoningSteps : thinkingSteps}
                      durationSeconds={((streamState.endedAt || Date.now()) - (streamState.startedAt || Date.now())) / 1000}
                    />

                    <ToolTimelinePanel
                      visible={toolTimelineVisible && !isStreaming}
                      timeline={messageToolTimeline}
                    />

                    <div
                      className={clsx(
                        'w-full rounded-2xl border px-4 py-2.5 shadow-sm',
                        isAssistant
                          ? 'border-border/70 bg-card/95 text-foreground'
                          : 'border-primary/10 bg-primary text-primary-foreground'
                      )}
                    >
                      <div
                        className={clsx(
                          'flex items-center gap-2 text-[10px] uppercase tracking-[0.24em]',
                          isAssistant ? 'text-muted-foreground' : 'text-primary-foreground/70',
                        )}
                      >
                        {isAssistant ? <Bot className="w-3.5 h-3.5" /> : <User className="w-3.5 h-3.5" />}
                        <span>{isAssistant ? 'AI' : 'You'}</span>
                        <span className="ml-auto font-mono tracking-[0.2em]">{formatTime(message.created_at)}</span>
                      </div>

                      <div
                        className={clsx(
                          'mt-1.5 text-[15px] leading-[1.65]',
                          isAssistant ? 'font-serif magazine-body' : 'font-sans font-medium',
                        )}
                      >
                        {showStreamingMeta && (
                          <div className="mb-2 flex min-h-7 items-center gap-2 text-[11px] uppercase tracking-[0.16em] text-muted-foreground">
                            {reasoningVisible && <span className="rounded-full border border-border/70 px-2 py-0.5">{labels.thinking}</span>}
                            {toolTimelineVisible && <span className="rounded-full border border-border/70 px-2 py-0.5">Tools</span>}
                          </div>
                        )}

                        {messageCitations.length > 0 && message.displayContent ? (
                          renderContentWithCitations(message.displayContent, (index) => {
                            onCitationClick(messageCitations[index]);
                          })
                        ) : message.displayContent ? (
                          <div className="whitespace-pre-wrap">
                            {message.displayContent}
                            {isStreaming && isAssistant && (
                              <span className="ml-0.5 inline-block h-4 w-[1px] animate-pulse bg-current align-middle" aria-hidden="true" />
                            )}
                          </div>
                        ) : isStreaming ? (
                          <div className={clsx('flex items-center gap-2 text-sm', isAssistant ? 'text-muted-foreground' : 'text-primary-foreground/80')}>
                            <Loader2 className="w-4 h-4 animate-spin" />
                            {labels.thinking}
                          </div>
                        ) : null}
                      </div>

                      {isActiveStreamMessage && (
                        <button
                          onClick={onStop}
                          className={clsx(
                            'mt-3 inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs transition-colors',
                            isAssistant
                              ? 'border border-border/70 bg-background/80 text-foreground hover:bg-muted'
                              : 'border border-primary-foreground/20 bg-primary-foreground/10 text-primary-foreground hover:bg-primary-foreground/20',
                          )}
                        >
                          <Square className="w-3 h-3" />
                          {labels.stop}
                        </button>
                      )}
                    </div>

                    <CitationPanel
                      visible={messageCitations.length > 0}
                      citations={safeCitations(messageCitations)}
                    />

                    {tokenCount !== undefined && tokenCount > 0 && !isStreaming && (
                      <div className="text-xs text-muted-foreground font-mono">
                        Token: {tokenCount.toLocaleString()}
                        {costValue > 0 && ` · ¥${costValue.toFixed(4)}`}
                      </div>
                    )}
                  </div>

                  {!isAssistant && (
                    <div className="mt-1 flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full border border-border/70 bg-card text-foreground shadow-sm">
                      <User className="w-4 h-4" />
                    </div>
                  )}
                </div>
              );
            })}

          <div ref={messagesEndRef} />
        </div>
      )}

      {streamState.error && (
        <div className="max-w-2xl mx-auto mt-6">
          <UnifiedErrorState
            title="对话流中断"
            description={streamState.error.message}
            retryLabel={labels.stop}
            onRetry={onStop}
          />
        </div>
      )}
    </div>
  );
}
