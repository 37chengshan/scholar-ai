import { AnimatePresence } from 'motion/react';
import { PanelRightOpen } from 'lucide-react';
import type { RefObject, ReactNode } from 'react';

import { ConfirmDialog } from '@/app/components/ConfirmDialog';
import { ConfirmationDialog } from '@/app/components/ConfirmationDialog';
import type { ChatStreamState } from '@/app/hooks/useChatStream';
import { ScopeBanner } from '@/app/components/ScopeBanner';
import { WorkspaceShell } from '@/app/components/layout/WorkspaceShell';
import { ComposerInput } from '@/features/chat/components/composer-input/ComposerInput';
import { MessageFeed } from '@/features/chat/components/message-feed/MessageFeed';
import { ChatRightPanel } from '@/features/chat/components/ChatRightPanel';
import { RunHeader } from '@/features/chat/components/workbench/RunHeader';
import { WorkflowShell } from '@/features/workflow/components/WorkflowShell';
import type { ThinkingStep } from '@/app/components/ThinkingProcess';
import type { ScopeType } from '@/app/components/ScopeBanner';

interface HandoffBannerData {
  originLabel: string;
  evidenceCount: number;
}

interface ChatWorkspaceLayoutProps {
  isZh: boolean;
  uiScope: {
    type: ScopeType | null;
    title?: string;
    errorMessage?: string;
  };
  handoffBanner: HandoffBannerData | null;
  runtimeRun: any;
  showRightPanel: boolean;
  renderMessages: any[];
  streamState: ChatStreamState;
  streamingMessageId: string | null;
  thinkingSteps: ThinkingStep[];
  messagesEndRef: RefObject<HTMLDivElement>;
  messageListRef: RefObject<HTMLDivElement>;
  handleCitationClick: (citation: any) => void;
  handleStop: () => void;
  handleSend: () => void;
  setInput: (value: string) => void;
  formatTime: (dateStr: string) => string;
  errorStage?: string;
  scopeHint: string;
  mode: 'auto' | 'rag' | 'agent';
  input: string;
  scopeLoading: boolean;
  sending: boolean;
  setMode: (mode: 'auto' | 'rag' | 'agent') => void;
  handleKeyDown: (event: React.KeyboardEvent) => void;
  panelStreamState: ChatStreamState;
  deferredRun: any;
  sessionTokens: number;
  sessionCost: number;
  setRightPanelOpen: (open: boolean) => void;
  handleExitScope: () => void;
  confirmation: { tool?: string; params?: Record<string, unknown> } | null;
  handleConfirmation: (approved: boolean) => void;
  showDeleteConfirm: boolean;
  confirmDeleteSession: () => void;
  cancelDeleteSession: () => void;
  labels: {
    noMessages: string;
    sendFirst: string;
    thinking: string;
    stop: string;
    placeholder: string;
    verify: string;
  };
  onVisibleRangeChange?: (startIndex: number, stopIndex: number) => void;
}

export function ChatWorkspaceLayout({
  isZh,
  uiScope,
  handoffBanner,
  runtimeRun,
  showRightPanel,
  renderMessages,
  streamState,
  streamingMessageId,
  thinkingSteps,
  messagesEndRef,
  messageListRef,
  handleCitationClick,
  handleStop,
  handleSend,
  setInput,
  formatTime,
  errorStage,
  scopeHint,
  mode,
  input,
  scopeLoading,
  sending,
  setMode,
  handleKeyDown,
  panelStreamState,
  deferredRun,
  sessionTokens,
  sessionCost,
  setRightPanelOpen,
  handleExitScope,
  confirmation,
  handleConfirmation,
  showDeleteConfirm,
  confirmDeleteSession,
  cancelDeleteSession,
  labels,
}: ChatWorkspaceLayoutProps) {
  return (
    <div className="editorial-app-shell relative flex h-full min-h-0 w-full overflow-hidden bg-background text-foreground">
      <WorkspaceShell
        layoutId="chat-workspace"
        main={(
          <div className="flex min-h-0 min-w-0 h-full flex-1 flex-col bg-background">
            <div className="shrink-0 border-b border-border/30 bg-background/60 backdrop-blur-sm">
              <WorkflowShell />
            </div>

            {uiScope.type && (
              <div className="shrink-0 border-b border-border/40 bg-muted/25">
                <ScopeBanner
                  type={uiScope.type}
                  title={uiScope.title}
                  errorMessage={uiScope.errorMessage}
                  onExitScope={handleExitScope}
                />
              </div>
            )}

            {handoffBanner ? (
              <div className="shrink-0 border-b border-border/40 bg-primary/[0.05] px-4 py-2.5 sm:px-6">
                <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                  <span className="rounded-full border border-primary/20 bg-primary/10 px-2 py-0.5 font-semibold text-primary">
                    {isZh ? `来自 ${handoffBanner.originLabel}` : `From ${handoffBanner.originLabel}`}
                  </span>
                  <span>
                    {isZh
                      ? '已为你预填下一条问题，确认后再发送。'
                      : 'A follow-up prompt is prefilled for review before sending.'}
                  </span>
                  {handoffBanner.evidenceCount > 0 ? (
                    <span>
                      {isZh
                        ? `${handoffBanner.evidenceCount} 条证据上下文已带入`
                        : `${handoffBanner.evidenceCount} evidence references were carried in`}
                    </span>
                  ) : null}
                </div>
              </div>
            ) : null}

            {runtimeRun && (
              <div className="shrink-0 border-b border-border/40 bg-muted/20">
                <RunHeader run={runtimeRun} />
              </div>
            )}

            <div className="min-h-0 min-w-0 flex flex-1 flex-col overflow-hidden bg-background">
              <div className="border-b border-border/30 bg-background/40 px-4 py-2.5 text-[11px] font-semibold text-muted-foreground sm:px-6">
                <div className="flex items-center justify-between gap-3">
                  <span>{isZh ? '对话' : 'Conversation'}</span>
                  {!showRightPanel ? (
                    <button
                      type="button"
                      onClick={() => setRightPanelOpen(true)}
                      className="hidden items-center gap-2 rounded-full border border-border/70 bg-paper-2 px-3 py-1.5 text-[10px] font-bold uppercase tracking-[0.12em] text-foreground/70 transition-colors hover:border-primary/20 hover:text-primary xl:inline-flex"
                      aria-label={isZh ? '展开右侧栏' : 'Show panel'}
                      title={isZh ? '展开右侧栏' : 'Show panel'}
                    >
                      <PanelRightOpen className="h-3.5 w-3.5" />
                      {isZh ? '展开侧注' : 'Show Trace'}
                    </button>
                  ) : null}
                </div>
              </div>
              <div className="editorial-reading-surface min-h-0 flex-1">
                <MessageFeed
                  renderMessages={renderMessages}
                  streamState={streamState}
                  currentMessageId={streamingMessageId || ''}
                  thinkingSteps={thinkingSteps}
                  labels={{
                    noMessages: labels.noMessages,
                    sendFirst: labels.sendFirst,
                    thinking: labels.thinking,
                    stop: labels.stop,
                  }}
                  isZh={isZh}
                  messagesEndRef={messagesEndRef}
                  scrollContainerRef={messageListRef}
                  onCitationClick={handleCitationClick}
                  onStop={handleStop}
                  onRetry={handleSend}
                  formatTime={formatTime}
                  onSuggest={(text) => {
                    setInput(text);
                  }}
                  errorStage={errorStage}
                  recoverable={runtimeRun?.recoverable}
                  partialAnswerAvailable={Boolean(streamState.contentBuffer)}
                />
              </div>
            </div>

            <div className="shrink-0 bg-background/75 backdrop-blur-md">
              <div className="px-4 pt-2 text-[11px] text-muted-foreground sm:px-6" aria-live="polite">
                {scopeHint}
              </div>
              <ComposerInput
                scopeType={uiScope.type}
                isZh={isZh}
                mode={mode}
                input={input}
                disabled={scopeLoading || sending}
                streaming={streamState.streamStatus === 'streaming'}
                placeholder={labels.placeholder}
                labels={{
                  mode: isZh ? '模式' : 'Mode',
                  verify: labels.verify,
                  sendKeyHint: isZh ? '↵ 发送' : '↵ TO SEND',
                }}
                onModeChange={setMode}
                onInputChange={setInput}
                onKeyDown={handleKeyDown}
                onSend={handleSend}
                onStop={handleStop}
              />
            </div>
          </div>
        )}
        inspector={
          showRightPanel ? (
            <AnimatePresence>
              <ChatRightPanel
                streamState={panelStreamState}
                activeRun={deferredRun}
                sessionTokens={sessionTokens}
                sessionCost={sessionCost}
                onStop={handleStop}
                onClose={() => setRightPanelOpen(false)}
                isZh={isZh}
                inline
              />
            </AnimatePresence>
          ) : undefined
        }
      />

      <ConfirmationDialog
        isOpen={!!confirmation}
        tool={confirmation?.tool || ''}
        params={confirmation?.params || {}}
        onApprove={() => handleConfirmation(true)}
        onReject={() => handleConfirmation(false)}
      />

      <ConfirmDialog
        isOpen={showDeleteConfirm}
        title={isZh ? '删除对话' : 'Delete Session'}
        message={
          isZh
            ? '确定要删除这个对话吗？删除后将无法恢复。'
            : 'Are you sure you want to delete this session? This cannot be undone.'
        }
        confirmLabel={isZh ? '删除' : 'Delete'}
        cancelLabel={isZh ? '取消' : 'Cancel'}
        variant="danger"
        onConfirm={confirmDeleteSession}
        onCancel={cancelDeleteSession}
      />
    </div>
  );
}
