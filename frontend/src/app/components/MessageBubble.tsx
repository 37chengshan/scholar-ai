/**
 * MessageBubble Component
 *
 * Displays a single chat message with role-based styling.
 * Supports user and assistant messages with different layouts.
 *
 * Usage:
 * ```tsx
 * <MessageBubble role="user" content="Hello!" />
 * <MessageBubble role="assistant" content="Hi there!" />
 * ```
 */

import { clsx } from 'clsx';
import { motion } from 'motion/react';
import { Bot, User, Copy, ThumbsUp, ThumbsDown, RefreshCw } from 'lucide-react';
import { useState } from 'react';

/**
 * Message role
 */
export type MessageRole = 'user' | 'assistant' | 'system';

/**
 * MessageBubble props
 */
export interface MessageBubbleProps {
  role: MessageRole;
  content: string;
  timestamp?: string;
  isStreaming?: boolean;
  onCopy?: () => void;
  onRetry?: () => void;
  className?: string;
}

/**
 * MessageBubble Component
 *
 * Renders a chat message with role-based styling.
 * User messages align right, assistant messages align left.
 */
export function MessageBubble({
  role,
  content,
  timestamp,
  isStreaming = false,
  onCopy,
  onRetry,
  className,
}: MessageBubbleProps) {
  const [copied, setCopied] = useState(false);

  const isUser = role === 'user';
  const isAssistant = role === 'assistant';

  /**
   * Handle copy to clipboard
   */
  const handleCopy = async () => {
    if (!content) return;

    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
      onCopy?.();
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  /**
   * Format timestamp
   */
  const formatTime = (ts?: string) => {
    if (!ts) return '';
    const date = new Date(ts);
    return date.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={clsx(
        'flex flex-col w-full group',
        isUser ? 'items-end' : 'items-start',
        className
      )}
    >
      {/* Header: Role & Timestamp */}
      <div
        className={clsx(
          'flex items-center gap-2 mb-1',
          isUser ? 'mr-1 flex-row-reverse' : 'ml-1'
        )}
      >
        {isAssistant && (
          <span className="text-[8px] font-bold uppercase tracking-[0.2em] text-primary flex items-center gap-1">
            <Bot className="w-3 h-3" />
            ScholarAI
          </span>
        )}
        {isUser && (
          <span className="text-[8px] font-bold uppercase tracking-[0.2em] text-foreground">
            You
          </span>
        )}
        {timestamp && (
          <span className="text-[8px] font-mono text-muted-foreground">
            {formatTime(timestamp)}
          </span>
        )}
      </div>

      {/* Message Content */}
      <div
        className={clsx(
          'max-w-[85%] px-4 py-3 shadow-sm',
          isUser
            ? 'bg-card border border-border/50 rounded-l-md rounded-tr-md'
            : 'bg-muted/20 border border-primary/20 rounded-r-md rounded-tl-md'
        )}
      >
        <p className="font-serif text-sm leading-[1.6] text-foreground/90 whitespace-pre-wrap">
          {content}
          {isStreaming && (
            <span className="inline-block w-1.5 h-4 bg-primary ml-0.5 animate-pulse" />
          )}
        </p>
      </div>

      {/* Actions (Assistant only) */}
      {isAssistant && !isStreaming && content && (
        <div
          className={clsx(
            'flex gap-3 mt-1.5 opacity-0 group-hover:opacity-100 transition-opacity ml-1'
          )}
        >
          <button
            onClick={handleCopy}
            className="text-muted-foreground hover:text-primary transition-colors flex items-center gap-1 text-[8px] uppercase tracking-[0.2em] font-bold"
          >
            <Copy className="w-2.5 h-2.5" />
            {copied ? 'Copied' : 'Copy'}
          </button>
          <button className="text-muted-foreground hover:text-primary transition-colors flex items-center gap-1 text-[8px] uppercase tracking-[0.2em] font-bold">
            <ThumbsUp className="w-2.5 h-2.5" />
            Good
          </button>
          <button className="text-muted-foreground hover:text-destructive transition-colors flex items-center gap-1 text-[8px] uppercase tracking-[0.2em] font-bold">
            <ThumbsDown className="w-2.5 h-2.5" />
            Bad
          </button>
          {onRetry && (
            <button
              onClick={onRetry}
              className="text-muted-foreground hover:text-primary transition-colors flex items-center gap-1 text-[8px] uppercase tracking-[0.2em] font-bold"
            >
              <RefreshCw className="w-2.5 h-2.5" />
              Retry
            </button>
          )}
        </div>
      )}
    </motion.div>
  );
}

export type { MessageBubbleProps as MessageBubblePropsType };