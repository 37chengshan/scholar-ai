/**
 * MessageThinkingPanel Component
 *
 * Thinking content display panel with 3-layer structure:
 * 1. Task type (single_paper / kb_qa / compare / general)
 * 2. Phase label (analyzing / retrieving / synthesizing)
 * 3. Thinking content (Markdown rendered reasoning buffer)
 *
 * Features:
 * - Tool execution timeline with status indicators
 * - Citation summary display
 * - Collapsed/expanded states
 * - Purple theme matching ThinkingProcess style
 *
 * Part of Agent-Native Chat architecture (D-19, D-20, D-21)
 */

import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  Brain,
  Loader2,
  CheckCircle,
  XCircle,
  ChevronDown,
  ChevronRight,
  BookOpen,
  FileText,
  GitCompare,
  MessageSquare,
  Search,
  Sparkles,
} from 'lucide-react';
import { clsx } from 'clsx';
import { MarkdownRenderer } from './MarkdownRenderer';
import { useLanguage } from '../contexts/LanguageContext';

// ============================================================================
// Type Definitions
// ============================================================================

/**
 * Agent processing phase
 */
export type AgentPhase = 'analyze' | 'plan' | 'execute' | 'synthesize' | 'respond';

/**
 * Task type from SessionStartData
 */
export type TaskType = 'single_paper' | 'kb_qa' | 'compare' | 'general';

/**
 * Tool timeline item for execution tracking
 */
export interface ToolTimelineItem {
  id: string;
  tool: string;
  label: string; // User-friendly label
  status: 'running' | 'success' | 'failed';
  summary?: string; // Result summary
  startedAt?: number;
  endedAt?: number;
}

/**
 * Citation item for source references
 */
export interface CitationItem {
  paper_id: string;
  title: string;
  pages: number[];
  hits: number;
}

/**
 * MessageThinkingPanel props
 */
export interface MessageThinkingPanelProps {
  /** Thinking/reasoning content buffer */
  reasoningBuffer: string;
  /** Tool execution timeline */
  toolTimeline: ToolTimelineItem[];
  /** Citation information */
  citations: CitationItem[];
  /** Current processing phase */
  currentPhase: AgentPhase;
  /** Human-readable phase label */
  phaseLabel: string;
  /** Task type identifier */
  taskType: TaskType;
  /** Whether panel is expanded */
  isExpanded: boolean;
  /** Optional className */
  className?: string;
  /** Callback when expand state changes */
  onExpandChange?: (expanded: boolean) => void;
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Get task type icon and label
 */
function getTaskTypeInfo(taskType: TaskType, isZh: boolean) {
  const taskTypes: Record<TaskType, { icon: React.ElementType; label: string; labelEn: string }> = {
    single_paper: {
      icon: FileText,
      label: '单论文问答',
      labelEn: 'Single Paper Q&A',
    },
    kb_qa: {
      icon: BookOpen,
      label: '知识库问答',
      labelEn: 'Knowledge Base Q&A',
    },
    compare: {
      icon: GitCompare,
      label: '对比分析',
      labelEn: 'Compare Analysis',
    },
    general: {
      icon: MessageSquare,
      label: '通用对话',
      labelEn: 'General Chat',
    },
  };
  return taskTypes[taskType];
}

/**
 * Get phase icon
 */
function getPhaseIcon(phase: AgentPhase): React.ElementType {
  const icons: Record<AgentPhase, React.ElementType> = {
    analyze: Brain,
    plan: Search,
    execute: Sparkles,
    synthesize: Sparkles,
    respond: MessageSquare,
  };
  return icons[phase];
}

/**
 * Get phase color
 */
function getPhaseColor(phase: AgentPhase): string {
  const colors: Record<AgentPhase, string> = {
    analyze: 'text-blue-500',
    plan: 'text-purple-500',
    execute: 'text-[#d35400]',
    synthesize: 'text-green-500',
    respond: 'text-slate-500',
  };
  return colors[phase];
}

/**
 * Format tool duration
 */
function formatDuration(isZh: boolean, startedAt?: number, endedAt?: number): string {
  if (!startedAt || !endedAt) return '';
  const ms = endedAt - startedAt;
  if (ms < 1000) return `${ms}ms`;
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return isZh ? `${seconds}秒` : `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  return isZh ? `${minutes}分钟` : `${minutes}m`;
}

// ============================================================================
// Sub-Components
// ============================================================================

/**
 * Loading spinner for running tools
 */
function LoadingSpinner({ className }: { className?: string }) {
  return (
    <Loader2
      className={clsx('w-4 h-4 animate-spin text-purple-500', className)}
    />
  );
}

/**
 * Status icon for tool execution
 */
function StatusIcon({ status, className }: { status: 'running' | 'success' | 'failed'; className?: string }) {
  if (status === 'running') {
    return <LoadingSpinner className={className} />;
  }
  if (status === 'success') {
    return <CheckCircle className={clsx('w-4 h-4 text-green-500', className)} />;
  }
  return <XCircle className={clsx('w-4 h-4 text-red-500', className)} />;
}

/**
 * Collapsed summary view
 */
function CollapsedSummary({
  taskType,
  phaseLabel,
  toolTimeline,
  isZh,
  onClick,
}: {
  taskType: TaskType;
  phaseLabel: string;
  toolTimeline: ToolTimelineItem[];
  isZh: boolean;
  onClick: () => void;
}) {
  const taskInfo = getTaskTypeInfo(taskType, isZh);
  const runningCount = toolTimeline.filter(t => t.status === 'running').length;
  const successCount = toolTimeline.filter(t => t.status === 'success').length;
  const TaskIcon = taskInfo.icon;

  const summaryText = isZh
    ? `${taskInfo.label} - ${phaseLabel}${runningCount > 0 ? ` (${runningCount}个工具执行中)` : ''}`
    : `${taskInfo.labelEn} - ${phaseLabel}${runningCount > 0 ? ` (${runningCount} tools running)` : ''}`;

  return (
    <button
      onClick={onClick}
      className="flex items-center gap-2 text-sm text-muted-foreground cursor-pointer hover:text-foreground py-1 transition-colors w-full"
    >
      <ChevronRight className="w-4 h-4" />
      <TaskIcon className="w-4 h-4 text-purple-400" />
      <span>{summaryText}</span>
      {successCount > 0 && (
        <span className="text-xs text-green-500 ml-auto">
          {isZh ? `${successCount}已完成` : `${successCount} done`}
        </span>
      )}
    </button>
  );
}

/**
 * Expanded full view
 */
function ExpandedView({
  taskType,
  currentPhase,
  phaseLabel,
  reasoningBuffer,
  toolTimeline,
  citations,
  isZh,
  onCollapse,
}: {
  taskType: TaskType;
  currentPhase: AgentPhase;
  phaseLabel: string;
  reasoningBuffer: string;
  toolTimeline: ToolTimelineItem[];
  citations: CitationItem[];
  isZh: boolean;
  onCollapse: () => void;
}) {
  const taskInfo = getTaskTypeInfo(taskType, isZh);
  const PhaseIcon = getPhaseIcon(currentPhase);
  const phaseColor = getPhaseColor(currentPhase);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
      className="space-y-3"
    >
      {/* Layer 1: Task Type */}
      <div className="flex items-center gap-2">
        <taskInfo.icon className="w-4 h-4 text-purple-400" />
        <span className="text-sm font-medium text-purple-600">
          {isZh ? taskInfo.label : taskInfo.labelEn}
        </span>
        <button
          onClick={onCollapse}
          className="ml-auto p-1 hover:bg-muted rounded transition-colors"
        >
          <ChevronDown className="w-4 h-4 text-muted-foreground" />
        </button>
      </div>

      {/* Layer 2: Phase Label */}
      <div className="flex items-center gap-2 pl-4">
        <PhaseIcon className={clsx('w-4 h-4', phaseColor)} />
        <span className="text-sm text-foreground">
          {phaseLabel}
        </span>
      </div>

      {/* Layer 3: Thinking Content */}
      {reasoningBuffer && (
        <div className="pl-6 pr-2">
          <div className="text-xs text-muted-foreground mb-1">
            {isZh ? '思考内容' : 'Thinking'}
          </div>
          <div className="max-h-64 overflow-y-auto bg-purple-50/30 rounded p-2 border border-purple-100">
            <MarkdownRenderer
              content={reasoningBuffer}
              className="text-xs"
            />
          </div>
        </div>
      )}

      {/* Tool Timeline */}
      {toolTimeline.length > 0 && (
        <div className="mt-4 border-t border-purple-100 pt-3 pl-6">
          <h4 className="text-xs font-semibold text-slate-500 mb-2">
            {isZh ? '工具执行' : 'Tool Execution'}
          </h4>
          <div className="space-y-2">
            {toolTimeline.map((tool) => (
              <motion.div
                key={tool.id}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.15 }}
                className="flex items-center gap-2 text-sm"
              >
                <StatusIcon status={tool.status} />
                <span className="text-foreground">{tool.label}</span>
                {tool.summary && (
                  <span className="text-slate-400 text-xs ml-2">
                    {tool.summary}
                  </span>
                )}
                {tool.startedAt && tool.endedAt && (
                  <span className="text-xs text-muted-foreground ml-auto">
                    {formatDuration(isZh, tool.startedAt, tool.endedAt)}
                  </span>
                )}
              </motion.div>
            ))}
          </div>
        </div>
      )}

      {/* Citations */}
      {citations.length > 0 && (
        <div className="mt-4 border-t border-purple-100 pt-3 pl-6">
          <h4 className="text-xs font-semibold text-slate-500 mb-2">
            {isZh ? '引用来源' : 'Citations'}
          </h4>
          <div className="space-y-1.5">
            {citations.map((citation) => (
              <div
                key={citation.paper_id}
                className="flex items-start gap-2 text-sm"
              >
                <BookOpen className="w-3 h-3 text-purple-400 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <span className="text-foreground truncate block">
                    {citation.title}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {isZh
                      ? `页码: ${citation.pages.join(', ')} | 引用次数: ${citation.hits}`
                      : `Pages: ${citation.pages.join(', ')} | Hits: ${citation.hits}`}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * MessageThinkingPanel Component
 *
 * Displays thinking process with 3-layer structure.
 * Collapsed state shows summary, expanded shows full details.
 */
export function MessageThinkingPanel({
  reasoningBuffer,
  toolTimeline,
  citations,
  currentPhase,
  phaseLabel,
  taskType,
  isExpanded,
  className,
  onExpandChange,
}: MessageThinkingPanelProps) {
  const [internalExpanded, setInternalExpanded] = useState(isExpanded);
  const { language } = useLanguage();
  const isZh = language === 'zh';

  // Use internal state if no external control
  const expanded = onExpandChange ? isExpanded : internalExpanded;

  const handleToggle = () => {
    if (onExpandChange) {
      onExpandChange(!expanded);
    } else {
      setInternalExpanded(!expanded);
    }
  };

  return (
    <div
      className={clsx(
        'border-l-2 border-[#8b5cf6]/30 pl-4 py-2 my-2 bg-purple-50/50 rounded-r-lg',
        className
      )}
    >
      <AnimatePresence mode="wait">
        {!expanded ? (
          <motion.div
            key="collapsed"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <CollapsedSummary
              taskType={taskType}
              phaseLabel={phaseLabel}
              toolTimeline={toolTimeline}
              isZh={isZh}
              onClick={handleToggle}
            />
          </motion.div>
        ) : (
          <motion.div
            key="expanded"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <ExpandedView
              taskType={taskType}
              currentPhase={currentPhase}
              phaseLabel={phaseLabel}
              reasoningBuffer={reasoningBuffer}
              toolTimeline={toolTimeline}
              citations={citations}
              isZh={isZh}
              onCollapse={handleToggle}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ============================================================================
// Exports
// ============================================================================

export type {
  MessageThinkingPanelProps as MessageThinkingPanelPropsType,
};