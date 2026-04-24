import { Bot, Copy, Loader2, Square, User, ArrowDown, Check } from 'lucide-react';
import { clsx } from 'clsx';
import { useState, useCallback } from 'react';
import type { ChatStreamState } from '@/app/hooks/useChatStream';
import type { ThinkingStep } from '@/app/components/ThinkingProcess';
import { renderContentWithCitations } from '@/app/components/CitationsPanel';
import { UnifiedErrorState } from '@/app/components/UnifiedFeedbackState';
import { ChatEmptyState } from './ChatEmptyState';
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
  isZh?: boolean;
  messagesEndRef: React.RefObject<HTMLDivElement>;
  scrollContainerRef?: React.RefObject<HTMLDivElement>;
  onCitationClick: (citation: CitationItem | undefined) => void;
  onStop: () => void;
  formatTime: (date: string) => string;
  onSuggest?: (text: string) => void;
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

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [text]);
  return (
    <button
      onClick={handleCopy}
      className="p-1 rounded transition-colors text-muted-foreground hover:bg-muted/60 hover:text-foreground"
      title="Copy"
    >
      {copied ? <Check className="w-3.5 h-3.5 text-green-500" /> : <Copy className="w-3.5 h-3.5" />}
    </button>
  );
}

export function MessageFeed({
  renderMessages,
  streamState,
  currentMessageId,
  thinkingSteps,
  labels,
  isZh = true,
  messagesEndRef,
  scrollContainerRef,
  onCitationClick,
  onStop,
  formatTime,
  onSuggest,
}: MessageFeedProps) {
  return (
    <div ref={scrollContainerRef} className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden">
      {renderMessages.length === 0 ? (
        <ChatEmptyState isZh={isZh} onSuggest={onSuggest} />
      ) : (
        <div className="mx-auto max-w-3xl w-full flex flex-col py-6 px-4 sm:px-6">
          {renderMessages.map((message, index) => {
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

              // Spacing: tighter for consecutive same-role messages
              const prevMessage = index > 0 ? renderMessages[index - 1] : null;
              const roleChanged = !prevMessage || prevMessage.role !== message.role;

              if (isAssistant) {
                // ─── AI Message: no bubble, left brand indicator ───
                return (
                  <div
                    key={message.id}
                    className={clsx('group', roleChanged ? 'mt-6' : 'mt-2', index === 0 && 'mt-0')}
                  >
                    {/* Avatar + role label row - only on role change */}
                    {roleChanged && (
                      <div className="flex items-center gap-2 mb-2">
                        <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
                          <Bot className="h-3.5 w-3.5" />
                        </div>
                        <span className="text-xs font-semibold text-foreground/80">ScholarAI</span>
                      </div>
                    )}

                    <div className="pl-9">
                      <ReasoningPanel
                        visible={reasoningVisible && !isStreaming}
                        steps={messageReasoningSteps.length > 0 ? messageReasoningSteps : thinkingSteps}
                        durationSeconds={((streamState.endedAt || Date.now()) - (streamState.startedAt || Date.now())) / 1000}
                      />

                      <ToolTimelinePanel
                        visible={toolTimelineVisible && !isStreaming}
                        timeline={messageToolTimeline}
                      />

                      {showStreamingMeta && (
                        <div className="mb-2 flex items-center gap-2 text-[11px] text-muted-foreground">
                          {reasoningVisible && (
                            <span className="inline-flex items-center gap-1 rounded-full border border-border/60 px-2.5 py-0.5 bg-muted/30">
                              <Loader2 className="w-3 h-3 animate-spin" />
                              {labels.thinking}
                            </span>
                          )}
                          {toolTimelineVisible && (
                            <span className="inline-flex items-center gap-1 rounded-full border border-border/60 px-2.5 py-0.5 bg-muted/30">Tools</span>
                          )}
                        </div>
                      )}

                      {/* Content - no bubble wrapper */}
                      <div className="text-sm leading-relaxed text-foreground/90">
                        {messageCitations.length > 0 && message.displayContent ? (
                          renderContentWithCitations(message.displayContent, (citationIndex) => {
                            onCitationClick(messageCitations[citationIndex]);
                          })
                        ) : message.displayContent ? (
                          <div className="whitespace-pre-wrap">
                            {message.displayContent}
                            {isStreaming && (
                              <span className="ml-0.5 inline-block h-4 w-[2px] animate-[pulse_1s_ease-in-out_infinite] bg-primary/60 align-middle" aria-hidden="true" />
                            )}
                          </div>
                        ) : isStreaming ? (
                          <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <Loader2 className="w-4 h-4 animate-spin" />
                            {labels.thinking}
                          </div>
                        ) : null}
                      </div>

                      {isActiveStreamMessage && (
                        <button
                          onClick={onStop}
                          className="mt-3 inline-flex items-center gap-1.5 rounded-full border border-border/60 bg-background/90 px-3 py-1.5 text-xs text-foreground hover:bg-muted transition-colors"
                        >
                          <Square className="w-3 h-3" />
                          {labels.stop}
                        </button>
                      )}

                      <CitationPanel
                        visible={messageCitations.length > 0}
                        citations={safeCitations(messageCitations)}
                      />

                      {/* Action bar: copy, token info */}
                      {!isStreaming && message.displayContent && (
                        <div className="flex items-center gap-2 mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
                          <CopyButton text={message.displayContent} />
                          {tokenCount !== undefined && tokenCount > 0 && (
                            <span
                              className="text-[10px] text-muted-foreground"
                              title={costValue > 0 ? `Token: ${tokenCount.toLocaleString()} · ¥${costValue.toFixed(4)}` : undefined}
                            >
                              {tokenCount.toLocaleString()} tokens
                              {costValue > 0 && ` · ¥${costValue.toFixed(4)}`}
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              }

              // ─── User Message: compact pill bubble, right-aligned ───
              return (
                <div
                  key={message.id}
                  className={clsx('flex justify-end', roleChanged ? 'mt-6' : 'mt-2', index === 0 && 'mt-0')}
                >
                  <div className="max-w-[75%]">
                    <div className="rounded-2xl rounded-br-md bg-primary text-primary-foreground px-4 py-2.5 shadow-sm">
                      <div className="text-sm leading-relaxed font-medium whitespace-pre-wrap">
                        {message.displayContent}
                      </div>
                    </div>
                    <div className="text-right mt-0.5">
                      <span className="text-[10px] text-muted-foreground">{formatTime(message.created_at)}</span>
                    </div>
                  </div>
                </div>
              );
            })}

          <div ref={messagesEndRef} />
        </div>
      )}

      {streamState.error && (
        <div className="max-w-2xl mx-auto mt-6 px-4">
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
