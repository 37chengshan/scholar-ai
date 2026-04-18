import { AlertCircle, Bot, Loader2, Square, User } from 'lucide-react';
import { clsx } from 'clsx';
import type { ChatStreamState } from '@/app/hooks/useChatStream';
import type { ThinkingStep } from '@/app/components/ThinkingProcess';
import { TypingText } from '@/app/components/TypingText';
import { renderContentWithCitations } from '@/app/components/CitationsPanel';
import { UnifiedEmptyState, UnifiedErrorState } from '@/app/components/UnifiedFeedbackState';
import { ReasoningPanel } from '@/features/chat/components/reasoning-panel/ReasoningPanel';
import { ToolTimelinePanel } from '@/features/chat/components/tool-timeline/ToolTimelinePanel';
import { CitationPanel } from '@/features/chat/components/citation-panel/CitationPanel';
import type { CitationItem, ExtendedChatMessage, ToolTimelineItem } from '@/features/chat/components/workspaceTypes';

interface MessageFeedCopy {
  noMessages: string;
  sendFirst: string;
  thinking: string;
  stop: string;
}

interface MessageFeedProps {
  localMessages: ExtendedChatMessage[];
  streamState: ChatStreamState;
  currentMessageId: string;
  thinkingSteps: ThinkingStep[];
  labels: MessageFeedCopy;
  messagesEndRef: React.RefObject<HTMLDivElement>;
  onCitationClick: (citation: CitationItem | undefined) => void;
  onStop: () => void;
  formatTime: (date: string) => string;
}

const safeToolTimeline = (timeline?: ToolTimelineItem[]) => (timeline || []).filter(Boolean);
const safeCitations = (citations?: CitationItem[]) => (citations || []).filter(Boolean);

export function MessageFeed({
  localMessages,
  streamState,
  currentMessageId,
  thinkingSteps,
  labels,
  messagesEndRef,
  onCitationClick,
  onStop,
  formatTime,
}: MessageFeedProps) {
  return (
    <div className="flex-1 overflow-y-auto px-6 py-5">
      {localMessages.length === 0 ? (
        <div className="max-w-2xl mx-auto mt-12">
          <UnifiedEmptyState title={labels.noMessages} description={labels.sendFirst} />
        </div>
      ) : (
        <div className="space-y-6 max-w-5xl mx-auto">
          {localMessages
            .filter((message) => message.role === 'user' || message.role === 'assistant')
            .map((message) => {
              const isStreaming = message.streamStatus === 'streaming';
              const isPlaceholder = message.id.startsWith('placeholder-') || message.id === currentMessageId;

              return (
                <div
                  key={message.id}
                  className={clsx('flex gap-3', message.role === 'user' ? 'justify-end' : 'justify-start')}
                >
                  {message.role === 'assistant' && (
                    <div className="w-7 h-7 flex items-center justify-center flex-shrink-0 border-l-2 border-primary/70 mt-4 mb-auto pl-1">
                      <span className="font-serif text-[10px] font-black uppercase tracking-widest text-ink">AI</span>
                    </div>
                  )}

                  <div className="flex-1 max-w-[84%] space-y-3">
                    <ReasoningPanel
                      visible={isStreaming && Boolean(message.reasoningBuffer || streamState.reasoningBuffer) && Boolean(message.isThinkingExpanded)}
                      steps={thinkingSteps}
                      durationSeconds={((streamState.endedAt || Date.now()) - (streamState.startedAt || Date.now())) / 1000}
                    />

                    <ToolTimelinePanel
                      visible={isStreaming && (((message.toolTimeline?.length || 0) > 0) || streamState.toolTimeline.length > 0)}
                      timeline={safeToolTimeline(message.toolTimeline || streamState.toolTimeline)}
                    />

                    <div
                      className={clsx(
                        'max-w-full font-serif text-[15px] leading-loose py-4 px-2',
                        message.role === 'user'
                          ? 'font-bold text-right bg-transparent rounded-none shadow-none text-foreground text-base leading-relaxed relative border-b border-zinc-200'
                          : 'bg-transparent text-foreground rounded-none shadow-none border-l-2 border-primary/60 pl-5 magazine-body max-w-prose mx-auto'
                      )}
                    >
                      {((message.citations?.length || 0) > 0 || streamState.citations.length > 0) && message.content ? (
                        renderContentWithCitations(message.content, (index) => {
                          const scopedCitations = safeCitations(
                            message.citations || (isPlaceholder ? streamState.citations : [])
                          );
                          onCitationClick(scopedCitations[index]);
                        })
                      ) : message.content ? (
                        isStreaming ? (
                          <TypingText text={message.content} className="text-[15px] leading-loose" />
                        ) : (
                          <div className="text-[15px] leading-loose whitespace-pre-wrap">{message.content}</div>
                        )
                      ) : isStreaming ? (
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <Loader2 className="w-4 h-4 animate-spin" />
                          {labels.thinking}
                        </div>
                      ) : null}

                      <div className="text-[10px] font-mono tracking-widest mt-2 uppercase text-ink/40">
                        {formatTime(message.created_at)}
                      </div>
                    </div>

                    <CitationPanel
                      visible={((message.citations?.length || 0) > 0) || (isPlaceholder && streamState.citations.length > 0)}
                      citations={safeCitations(message.citations || streamState.citations)}
                    />

                    {(message.tokensUsed || streamState.tokensUsed) && !isStreaming && (
                      <div className="text-xs text-muted-foreground font-mono mt-1">
                        Token: {(message.tokensUsed || streamState.tokensUsed).toLocaleString()}
                        {(message.cost || streamState.cost) > 0 && ` · ¥${(message.cost || streamState.cost).toFixed(4)}`}
                      </div>
                    )}

                    {isStreaming && (
                      <button
                        onClick={onStop}
                        className="flex items-center gap-1 px-2.5 py-1 border border-zinc-200 bg-zinc-50 hover:bg-zinc-100 text-xs text-zinc-600 hover:text-zinc-900 transition-colors"
                      >
                        <Square className="w-3 h-3" />
                        {labels.stop}
                      </button>
                    )}
                  </div>

                  {message.role === 'user' && (
                    <div className="w-8 h-8 border border-zinc-200 bg-zinc-50 flex items-center justify-center flex-shrink-0">
                      <User className="w-4 h-4 text-muted-foreground" />
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
