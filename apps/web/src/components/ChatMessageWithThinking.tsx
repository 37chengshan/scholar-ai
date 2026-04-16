/**
 * ChatMessageWithThinking Component
 *
 * Integrates ThinkingStatusLine with message content, citations,
 * and expandable thinking details (steps, tool calls, token usage).
 *
 * Part of Agent-Native Chat architecture.
 */

import { clsx } from 'clsx';
import { useState } from 'react';
import { ThinkingStatusLine, ThinkingStatus } from './ThinkingStatusLine';

/**
 * Citation reference for AI response
 */
export interface Citation {
  /** Source document name */
  source: string;
  /** Excerpt from the source */
  excerpt: string;
  /** Page number if available */
  page?: number;
}

/**
 * Step in the thinking process
 */
export interface Step {
  /** Step name/identifier */
  name: string;
  /** Step description */
  description: string;
  /** Step status */
  status?: 'pending' | 'running' | 'completed' | 'failed';
}

/**
 * Tool call record
 */
export interface ToolCall {
  /** Tool name */
  name: string;
  /** Input parameters */
  input: Record<string, unknown>;
  /** Output result */
  output?: string | Record<string, unknown>;
  /** Duration in ms */
  duration_ms?: number;
}

/**
 * Token usage statistics
 */
export interface TokenUsage {
  /** Input tokens */
  input: number;
  /** Output tokens */
  output: number;
  /** Total tokens */
  total: number;
}

/**
 * ChatMessageWithThinking props
 */
export interface ChatMessageWithThinkingProps {
  /** Message content text */
  message: string;
  /** Citation references */
  citations?: Citation[];
  /** Whether message is actively streaming */
  isStreaming: boolean;
  /** Current thinking status */
  thinkingStatus?: ThinkingStatus;
  /** Thinking summary text */
  thinkingSummary?: string;
  /** Step progress information */
  stepProgress?: { current: number; total: number };
  /** Duration in milliseconds */
  duration_ms?: number;
  /** Thinking steps for details view */
  steps?: Step[];
  /** Tool calls for details view */
  toolCalls?: ToolCall[];
  /** Token usage statistics */
  tokenUsage?: TokenUsage;
}

/**
 * Check if there are details to show
 */
function hasDetails(
  steps?: Step[],
  toolCalls?: ToolCall[],
  tokenUsage?: TokenUsage
): boolean {
  return Boolean(
    (steps && steps.length > 0) ||
    (toolCalls && toolCalls.length > 0) ||
    tokenUsage
  );
}

/**
 * Citation Item Component
 */
function CitationItem({ citation }: { citation: Citation }) {
  return (
    <div
      className={clsx(
        'flex items-start gap-2 px-3 py-2 rounded-md',
        'bg-muted/20 border border-muted/30',
        'text-sm'
      )}
    >
      <span className="flex-shrink-0 text-muted-foreground">
        [{citation.page ?? 'ref'}]
      </span>
      <div className="flex-1 min-w-0">
        <span className="font-medium text-foreground">
          {citation.source}
        </span>
        <p className="text-muted-foreground text-xs mt-0.5 truncate">
          {citation.excerpt}
        </p>
      </div>
    </div>
  );
}

/**
 * Thinking Details Panel (inline expanded view)
 *
 * This is a lightweight inline view that can be replaced with
 * a proper ThinkingDetailModal component later.
 */
function ThinkingDetailsPanel({
  steps,
  toolCalls,
  tokenUsage,
  onClose,
}: {
  steps?: Step[];
  toolCalls?: ToolCall[];
  tokenUsage?: TokenUsage;
  onClose: () => void;
}) {
  return (
    <div
      className={clsx(
        'mt-2 p-4 rounded-lg',
        'bg-popover border border-border',
        'shadow-md'
      )}
      role="dialog"
      aria-label="Thinking details"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold">Thinking Details</h4>
        <button
          type="button"
          aria-label="Close"
          onClick={onClose}
          className={clsx(
            'p-1 rounded hover:bg-muted/50',
            'text-muted-foreground hover:text-foreground',
            'transition-colors'
          )}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>

      {/* Steps */}
      {steps && steps.length > 0 && (
        <div className="mb-3">
          <h5 className="text-xs font-medium text-muted-foreground mb-2">
            Steps
          </h5>
          <ul className="space-y-1">
            {steps.map((step, idx) => (
              <li
                key={idx}
                className={clsx(
                  'flex items-center gap-2 text-sm',
                  step.status === 'completed' && 'text-green-600',
                  step.status === 'running' && 'text-blue-600',
                  step.status === 'failed' && 'text-red-600',
                  step.status === 'pending' && 'text-muted-foreground'
                )}
              >
                <span className="w-4 h-4 flex items-center justify-center">
                  {step.status === 'completed' && '✓'}
                  {step.status === 'running' && '◐'}
                  {step.status === 'failed' && '✗'}
                  {step.status === 'pending' && '○'}
                </span>
                <span className="font-medium">{step.name}</span>
                <span className="text-muted-foreground text-xs">
                  {step.description}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Tool Calls */}
      {toolCalls && toolCalls.length > 0 && (
        <div className="mb-3">
          <h5 className="text-xs font-medium text-muted-foreground mb-2">
            Tool Calls
          </h5>
          <ul className="space-y-1">
            {toolCalls.map((tool, idx) => (
              <li
                key={idx}
                className={clsx(
                  'flex items-center gap-2 text-sm p-2 rounded',
                  'bg-muted/20'
                )}
              >
                <span className="font-mono text-xs font-medium text-blue-600">
                  {tool.name}
                </span>
                {tool.duration_ms && (
                  <span className="text-xs text-muted-foreground tabular-nums">
                    {tool.duration_ms}ms
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Token Usage */}
      {tokenUsage && (
        <div>
          <h5 className="text-xs font-medium text-muted-foreground mb-2">
            Token Usage
          </h5>
          <div className="flex items-center gap-4 text-sm">
            <span>
              Input: <span className="tabular-nums">{tokenUsage.input}</span>
            </span>
            <span>
              Output: <span className="tabular-nums">{tokenUsage.output}</span>
            </span>
            <span className="font-medium">
              Total: <span className="tabular-nums">{tokenUsage.total}</span>
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * ChatMessageWithThinking Component
 *
 * Structure:
 * 1. ThinkingStatusLine (top) - shown during streaming
 * 2. Message Content - main text
 * 3. Citations (bottom) - reference links
 * 4. ThinkingDetailsPanel (expandable) - shown when expanded
 */
export function ChatMessageWithThinking({
  message,
  citations,
  isStreaming,
  thinkingStatus = 'idle',
  thinkingSummary = 'Ready to process',
  stepProgress,
  duration_ms,
  steps,
  toolCalls,
  tokenUsage,
}: ChatMessageWithThinkingProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const showDetails = hasDetails(steps, toolCalls, tokenUsage);

  const handleExpand = () => {
    setIsExpanded(true);
  };

  const handleCloseDetails = () => {
    setIsExpanded(false);
  };

  return (
    <div
      data-testid="chat-message-container"
      className={clsx('flex flex-col gap-2', 'max-w-full')}
    >
      {/* Thinking Status Line - shown during streaming */}
      {isStreaming && (
        <ThinkingStatusLine
          status={thinkingStatus}
          summary={thinkingSummary}
          stepProgress={stepProgress}
          duration_ms={duration_ms}
          isStreaming={isStreaming}
          hasDetails={showDetails}
          onExpand={handleExpand}
        />
      )}

      {/* Expanded Details Panel */}
      {isExpanded && (
        <ThinkingDetailsPanel
          steps={steps}
          toolCalls={toolCalls}
          tokenUsage={tokenUsage}
          onClose={handleCloseDetails}
        />
      )}

      {/* Message Content */}
      {message && (
        <div
          className={clsx(
            'prose prose-sm max-w-none',
            'px-3 py-2 rounded-md',
            'bg-background'
          )}
        >
          {message}
        </div>
      )}

      {/* Citations */}
      {citations && citations.length > 0 && (
        <div className="flex flex-col gap-1 mt-1">
          {citations.map((citation, idx) => (
            <CitationItem key={idx} citation={citation} />
          ))}
        </div>
      )}
    </div>
  );
}

export type { ChatMessageWithThinkingProps as ChatMessageWithThinkingPropsType };