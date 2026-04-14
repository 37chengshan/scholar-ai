/**
 * MessageThinkingHeader Component (Think Capsule)
 *
 * Displays the thinking status and content summary for AI agent messages.
 * Part of Agent-Native architecture - shows Planner->Executor->Verifier chain.
 *
 * Default expand strategy:
 * - streaming (generating): Think expanded by default
 * - completed (history): Think collapsed by default
 * - error / cancelled: Think expanded by default
 *
 * @see D-19, D-20, D-21 design specs
 */

import { useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  Brain,
  Loader2,
  ChevronDown,
  ChevronRight,
  Square,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Route,
  Search,
  ListChecks,
  Play,
  Sparkles,
} from 'lucide-react';
import { cn } from './ui/utils';
import { useLanguage } from '../contexts/LanguageContext';

/**
 * AgentPhase type
 * Represents the current phase of the agent execution cycle
 */
export type AgentPhase =
  | 'idle'
  | 'routing'
  | 'analyzing'
  | 'planning'
  | 'executing'
  | 'synthesizing'
  | 'completed'
  | 'error'
  | 'cancelled';

/**
 * MessageThinkingHeader props
 */
export interface MessageThinkingHeaderProps {
  /** Current agent phase */
  phase: AgentPhase;
  /** Human-readable phase label (localized) */
  phaseLabel: string;
  /** Whether the agent is actively streaming/generating */
  isStreaming: boolean;
  /** Whether the thinking capsule is currently expanded */
  isExpanded: boolean;
  /** Callback to toggle expand/collapse state */
  onToggleExpand: () => void;
  /** Optional callback to stop streaming (shown when streaming) */
  onStop?: () => void;
  /** Optional summary text to show when expanded */
  summary?: string;
  /** Optional duration in seconds */
  duration?: number;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Phase icon mapping
 * Each phase has a distinctive icon for visual clarity
 */
const PHASE_ICONS: Record<AgentPhase, React.ElementType> = {
  idle: Brain,
  routing: Route,
  analyzing: Search,
  planning: ListChecks,
  executing: Play,
  synthesizing: Sparkles,
  completed: CheckCircle2,
  error: AlertCircle,
  cancelled: XCircle,
};

/**
 * Phase color mapping
 * Visual indication of phase status
 */
const PHASE_COLORS: Record<AgentPhase, string> = {
  idle: 'text-slate-400',
  routing: 'text-blue-500',
  analyzing: 'text-indigo-500',
  planning: 'text-purple-500',
  executing: 'text-orange-500',
  synthesizing: 'text-teal-500',
  completed: 'text-green-500',
  error: 'text-red-500',
  cancelled: 'text-slate-500',
};

/**
 * Phase background colors (for capsule styling)
 */
const PHASE_BG_COLORS: Record<AgentPhase, string> = {
  idle: 'bg-slate-50',
  routing: 'bg-blue-50',
  analyzing: 'bg-indigo-50',
  planning: 'bg-purple-50',
  executing: 'bg-orange-50',
  synthesizing: 'bg-teal-50',
  completed: 'bg-green-50',
  error: 'bg-red-50',
  cancelled: 'bg-slate-100',
};

/**
 * Localized text labels
 */
const getLocalizedText = (isZh: boolean) => ({
  thinkingProcess: isZh ? '思考过程' : 'Thinking',
  stop: isZh ? '停止' : 'Stop',
  expand: isZh ? '展开' : 'Expand',
  collapse: isZh ? '折叠' : 'Collapse',
  seconds: isZh ? '秒' : 's',
  steps: isZh ? '步' : 'steps',
});

/**
 * MessageThinkingHeader Component
 *
 * Think Capsule with expand/collapse functionality, phase indicator,
 * streaming animation, and stop button.
 */
export function MessageThinkingHeader({
  phase,
  phaseLabel,
  isStreaming,
  isExpanded,
  onToggleExpand,
  onStop,
  summary,
  duration,
  className,
}: MessageThinkingHeaderProps) {
  const { language } = useLanguage();
  const isZh = language === 'zh';
  const t = getLocalizedText(isZh);

  // Get phase-specific icon and colors
  const PhaseIcon = PHASE_ICONS[phase];
  const phaseColor = PHASE_COLORS[phase];
  const phaseBgColor = PHASE_BG_COLORS[phase];

  // Handle stop click (prevent toggle expansion)
  const handleStopClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      onStop?.();
    },
    [onStop]
  );

  // Handle toggle click
  const handleToggleClick = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      onToggleExpand();
    },
    [onToggleExpand]
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: -4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={cn(
        'flex flex-col rounded-lg border border-slate-200/50 overflow-hidden',
        phaseBgColor,
        className
      )}
    >
      {/* Header row - clickable to toggle expand */}
      <div
        className={cn(
          'flex items-center gap-2 px-3 py-2 cursor-pointer',
          'hover:bg-slate-100/50 transition-colors',
          'select-none'
        )}
        onClick={handleToggleClick}
        role="button"
        aria-expanded={isExpanded}
        aria-label={isExpanded ? t.collapse : t.expand}
      >
        {/* Phase indicator icon */}
        <div className={cn('flex-shrink-0', phaseColor)}>
          {isStreaming ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <PhaseIcon className="w-4 h-4" />
          )}
        </div>

        {/* Phase label */}
        <div className="flex items-center gap-1.5 flex-1 min-w-0">
          <span className="text-sm font-medium text-slate-700 truncate">
            {isStreaming ? t.thinkingProcess : phaseLabel}
          </span>
          {duration !== undefined && !isStreaming && (
            <span className="text-xs text-slate-500">
              {duration}{t.seconds}
            </span>
          )}
        </div>

        {/* Expand/Collapse indicator */}
        <button
          type="button"
          className={cn(
            'flex-shrink-0 p-1 rounded',
            'text-slate-400 hover:text-slate-600',
            'hover:bg-slate-200/50 transition-colors',
            'focus:outline-none focus:ring-1 focus:ring-slate-300'
          )}
          aria-label={isExpanded ? t.collapse : t.expand}
        >
          {isExpanded ? (
            <ChevronDown className="w-4 h-4" />
          ) : (
            <ChevronRight className="w-4 h-4" />
          )}
        </button>

        {/* Stop button (only when streaming) */}
        {isStreaming && onStop && (
          <button
            type="button"
            onClick={handleStopClick}
            className={cn(
              'flex-shrink-0 ml-1 px-2 py-1 rounded-md',
              'text-red-600 hover:text-red-700',
              'bg-red-50 hover:bg-red-100',
              'border border-red-200',
              'text-xs font-medium',
              'transition-colors',
              'focus:outline-none focus:ring-1 focus:ring-red-300'
            )}
            aria-label={t.stop}
          >
            <Square className="w-3 h-3" />
          </button>
        )}
      </div>

      {/* Expanded content */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.15, ease: 'easeInOut' }}
            className="overflow-hidden"
          >
            <div className="px-3 pb-2 pt-1 border-t border-slate-200/30">
              {/* Summary content */}
              {summary ? (
                <div className="text-sm text-slate-600 whitespace-pre-wrap">
                  {summary}
                </div>
              ) : (
                <div className="text-sm text-slate-500 italic">
                  {isStreaming
                    ? isZh
                      ? '正在思考...'
                      : 'Thinking...'
                    : isZh
                      ? '无思考内容'
                      : 'No thinking content'}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

export type { MessageThinkingHeaderProps as MessageThinkingHeaderPropsType };