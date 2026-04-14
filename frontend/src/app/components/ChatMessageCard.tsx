/**
 * ChatMessageCard Component
 *
 * Message card component integrating MessageThinkingHeader + MessageThinkingPanel + main content.
 * Supports user and assistant messages with thinking process display.
 *
 * Features:
 * - Role-based styling (user vs assistant)
 * - Thinking header with phase indicator and expand/collapse
 * - Thinking panel with tool timeline and citations
 * - Markdown rendering for main content
 * - Citation panel for reference sources
 * - Streaming status indicators
 *
 * Part of Agent-Native Chat architecture (D-19, D-20, D-21)
 */

import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Bot, User, Clock } from 'lucide-react';
import { cn } from './ui/utils';
import { useLanguage } from '../contexts/LanguageContext';
import { MarkdownRenderer } from './MarkdownRenderer';
import { CitationsPanel } from './CitationsPanel';
import { MessageThinkingHeader, AgentPhase as HeaderAgentPhase } from './MessageThinkingHeader';
import {
  MessageThinkingPanel,
  AgentPhase as PanelAgentPhase,
  ToolTimelineItem,
  CitationItem,
  TaskType,
} from './MessageThinkingPanel';
import { PaperCitation } from '@/types/chat';

// ============================================================================
// Type Definitions
// ============================================================================

/**
 * Stream status for message
 */
export type StreamStatus = 'idle' | 'streaming' | 'completed' | 'error' | 'cancelled';

/**
 * Complete ChatMessage type
 */
export interface ChatMessage {
  /** Unique message ID */
  id: string;
  /** Message role (user or assistant) */
  role: 'user' | 'assistant';
  /** Main message content */
  content: string;
  /** Thinking/reasoning buffer (only for assistant) */
  reasoningBuffer?: string;
  /** Current agent phase */
  phase?: HeaderAgentPhase;
  /** Human-readable phase label */
  phaseLabel?: string;
  /** Task type identifier */
  taskType?: TaskType;
  /** Tool execution timeline */
  toolTimeline?: ToolTimelineItem[];
  /** Paper citations */
  citations?: PaperCitation[];
  /** Whether thinking panel is expanded (user-controlled) */
  isThinkingExpanded?: boolean;
  /** Stream status */
  streamStatus?: StreamStatus;
  /** Message timestamp */
  timestamp?: number;
}

/**
 * ChatMessageCard props
 */
export interface ChatMessageCardProps {
  /** Message data */
  message: ChatMessage;
  /** Whether message is actively streaming */
  isStreaming?: boolean;
  /** Callback when stop button is clicked */
  onStop?: () => void;
  /** Callback when expand state changes */
  onToggleExpand?: () => void;
  /** Additional CSS classes */
  className?: string;
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Format timestamp to readable time
 */
function formatTime(timestamp: number | undefined, isZh: boolean): string {
  if (!timestamp) return '';
  const date = new Date(timestamp);
  return date.toLocaleTimeString(isZh ? 'zh-CN' : 'en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: isZh ? false : true,
  });
}

/**
 * Determine default expand state based on stream status
 * - streaming: Think expanded by default
 * - completed: Think collapsed by default
 * - error/cancelled: Think expanded by default
 */
function getDefaultExpandState(streamStatus: StreamStatus): boolean {
  if (streamStatus === 'streaming') return true;
  if (streamStatus === 'error' || streamStatus === 'cancelled') return true;
  return false; // completed or idle
}

/**
 * Map HeaderAgentPhase to PanelAgentPhase
 * Note: The phases have different naming conventions
 */
function mapPhaseToPanelPhase(phase: HeaderAgentPhase): PanelAgentPhase {
  const phaseMap: Partial<Record<HeaderAgentPhase, PanelAgentPhase>> = {
    analyzing: 'analyze',
    planning: 'plan',
    executing: 'execute',
    synthesizing: 'synthesize',
  };
  return phaseMap[phase] || 'analyze';
}

/**
 * Convert PaperCitation to CitationItem for MessageThinkingPanel
 */
function convertPaperCitationsToCitationItems(citations: PaperCitation[]): CitationItem[] {
  return citations.map((c) => ({
    paper_id: c.paper_id,
    title: c.title,
    pages: [c.page],
    hits: Math.round(c.score * 10), // Approximate hit count from relevance score
  }));
}

// ============================================================================
// Sub-Components
// ============================================================================

/**
 * Avatar component for message role
 */
function MessageAvatar({ role }: { role: 'user' | 'assistant' }) {
  const isAssistant = role === 'assistant';

  return (
    <div
      className={cn(
        'flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center',
        isAssistant
          ? 'bg-primary/10 text-primary'
          : 'bg-slate-100 text-slate-600'
      )}
    >
      {isAssistant ? (
        <Bot className="w-4 h-4" />
      ) : (
        <User className="w-4 h-4" />
      )}
    </div>
  );
}

/**
 * Streaming cursor indicator
 */
function StreamingCursor() {
  return (
    <span className="inline-block w-1.5 h-4 bg-primary ml-0.5 animate-pulse" />
  );
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * ChatMessageCard Component
 *
 * Renders a complete message card with:
 * 1. Role avatar and timestamp header
 * 2. Thinking section (header + panel) for assistant messages
 * 3. Main content (Markdown rendered)
 * 4. Citation panel
 */
export function ChatMessageCard({
  message,
  isStreaming = false,
  onStop,
  onToggleExpand,
  className,
}: ChatMessageCardProps) {
  const { language } = useLanguage();
  const isZh = language === 'zh';
  const isAssistant = message.role === 'assistant';

  // Use user-controlled state if provided, otherwise use default
  const [internalExpanded, setInternalExpanded] = useState(
    getDefaultExpandState(message.streamStatus || 'idle')
  );

  const isThinkingExpanded = useMemo(() => {
    if (message.isThinkingExpanded !== undefined) {
      return message.isThinkingExpanded;
    }
    return internalExpanded;
  }, [message.isThinkingExpanded, internalExpanded]);

  // Toggle expand handler
  const handleToggleExpand = () => {
    if (onToggleExpand) {
      onToggleExpand();
    } else {
      setInternalExpanded(!internalExpanded);
    }
  };

  // Determine if streaming from message status or prop
  const effectiveIsStreaming = isStreaming || message.streamStatus === 'streaming';

  // Determine phase label
  const phaseLabel = message.phaseLabel || (isZh ? '处理完成' : 'Completed');

  // Convert citations for MessageThinkingPanel if needed
  const thinkingCitations = message.citations
    ? convertPaperCitationsToCitationItems(message.citations)
    : [];

  // Localized labels
  const t = {
    user: isZh ? '你' : 'You',
    ai: isZh ? 'ScholarAI' : 'ScholarAI',
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={cn(
        'flex flex-col gap-2 rounded-xl border bg-white p-4 shadow-sm',
        'border-slate-200/50',
        className
      )}
    >
      {/* Role Header */}
      <div className="flex items-center gap-2">
        <MessageAvatar role={message.role} />
        <span className="text-sm font-medium text-slate-700">
          {isAssistant ? t.ai : t.user}
        </span>
        {message.timestamp && (
          <div className="flex items-center gap-1 text-xs text-slate-400 ml-auto">
            <Clock className="w-3 h-3" />
            <span>{formatTime(message.timestamp, isZh)}</span>
          </div>
        )}
      </div>

      {/* Thinking Section (Assistant only) */}
      {isAssistant && message.reasoningBuffer && (
        <AnimatePresence mode="wait">
          <motion.div
            key="thinking-section"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
          >
            {/* Thinking Header */}
            <MessageThinkingHeader
              phase={message.phase || 'completed'}
              phaseLabel={phaseLabel}
              isStreaming={effectiveIsStreaming}
              isExpanded={isThinkingExpanded}
              onToggleExpand={handleToggleExpand}
              onStop={onStop}
              summary={message.reasoningBuffer.slice(0, 200)}
            />

            {/* Thinking Panel (expanded view) */}
            <AnimatePresence>
              {isThinkingExpanded && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.15, ease: 'easeInOut' }}
                  className="overflow-hidden"
                >
                  <MessageThinkingPanel
                    reasoningBuffer={message.reasoningBuffer || ''}
                    toolTimeline={message.toolTimeline || []}
                    citations={thinkingCitations}
                    currentPhase={mapPhaseToPanelPhase(message.phase || 'completed')}
                    phaseLabel={phaseLabel}
                    taskType={message.taskType || 'general'}
                    isExpanded={true}
                  />
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        </AnimatePresence>
      )}

      {/* Main Content */}
      <div className="mt-2 min-h-[20px]">
        {message.content ? (
          <MarkdownRenderer
            content={message.content}
            className="text-sm leading-relaxed"
          />
        ) : effectiveIsStreaming ? (
          <div className="text-sm text-slate-500 italic">
            {isZh ? '正在生成回答...' : 'Generating response...'}
            <StreamingCursor />
          </div>
        ) : null}
        {effectiveIsStreaming && message.content && <StreamingCursor />}
      </div>

      {/* Citation Panel */}
      {message.citations && message.citations.length > 0 && (
        <CitationsPanel citations={message.citations} className="mt-3" />
      )}
    </motion.div>
  );
}

// ============================================================================
// Exports
// ============================================================================

// Note: ChatMessage and StreamStatus are already exported at their definitions
export type {
  ChatMessageCardProps as ChatMessageCardPropsType,
};