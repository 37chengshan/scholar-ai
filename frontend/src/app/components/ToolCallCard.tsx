/**
 * ToolCallCard Component
 *
 * Generic tool call card with compact/expanded states (D-04).
 * Shows icon + name + status + duration in compact mode.
 * Shows parameters JSON and result in expanded mode.
 *
 * Part of Phase 28: Chat Frontend Enhancement
 */

import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  ShieldCheck,
  Upload,
  FilePlus,
  FileEdit,
  List,
  FileText,
  Search,
  Globe,
  Quote,
  Notebook,
  BookOpen,
  Combine,
  Terminal,
  MessageSquare,
  Trash2,
  Wrench,
  ChevronDown,
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
} from 'lucide-react';
import { clsx } from 'clsx';
import { useLanguage } from '../contexts/LanguageContext';
import { ToolCall, TOOL_DISPLAY_CONFIG } from '../../types/chat';
import { Badge } from './ui/badge';

/**
 * Icon mapping from TOOL_DISPLAY_CONFIG icon names to lucide-react components
 */
const ICON_MAP: Record<string, React.ElementType> = {
  ShieldCheck,
  Upload,
  FilePlus,
  FileEdit,
  List,
  FileText,
  Search,
  Globe,
  Quote,
  Notebook,
  BookOpen,
  Combine,
  Terminal,
  MessageSquare,
  Trash2,
};

/**
 * Format duration in ms or s
 */
function formatDuration(toolCall: ToolCall): string {
  const ms = toolCall.duration ?? (toolCall.completedAt ? toolCall.completedAt - toolCall.startedAt : 0);
  if (ms === 0 && toolCall.status === 'pending') return '—';
  if (ms === 0 && toolCall.status === 'running') return '...';
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

/**
 * Get status label
 */
function getStatusLabel(status: ToolCall['status'], isZh: boolean): string {
  const labels: Record<ToolCall['status'], { zh: string; en: string }> = {
    pending: { zh: '等待中', en: 'Pending' },
    running: { zh: '执行中', en: 'Running' },
    success: { zh: '完成', en: 'Success' },
    error: { zh: '失败', en: 'Failed' },
  };
  return isZh ? labels[status].zh : labels[status].en;
}

/**
 * ToolCallCard Props
 */
interface ToolCallCardProps {
  toolCall: ToolCall;
  className?: string;
}

/**
 * ToolCallCard Component
 *
 * Compact: icon + name + status badge + duration
 * Expanded: parameters JSON + result preview
 */
export function ToolCallCard({ toolCall, className }: ToolCallCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const { language } = useLanguage();
  const isZh = language === 'zh';

  const config = TOOL_DISPLAY_CONFIG[toolCall.tool];
  const displayName = config?.displayName ?? toolCall.tool;
  const iconName = config?.icon ?? 'Wrench';
  const IconComponent = ICON_MAP[iconName] ?? Wrench;

  // Status colors
  const statusColors: Record<ToolCall['status'], string> = {
    pending: 'text-muted-foreground',
    running: 'text-[#d35400]',
    success: 'text-green-600',
    error: 'text-destructive',
  };

  // Badge variants
  const badgeClasses: Record<ToolCall['status'], string> = {
    pending: 'bg-muted text-muted-foreground',
    running: 'bg-primary/10 text-primary',
    success: 'bg-green-100 text-green-700',
    error: 'bg-destructive/10 text-destructive',
  };

  // Status icon
  const StatusIcon = {
    pending: Clock,
    running: Loader2,
    success: CheckCircle2,
    error: XCircle,
  }[toolCall.status];

  const t = {
    parameters: isZh ? '参数' : 'Parameters',
    result: isZh ? '结果' : 'Result',
  };

  const duration = formatDuration(toolCall);
  const hasResult = toolCall.result !== undefined && toolCall.result !== null;

  return (
    <div
      className={clsx(
        'rounded-lg border border-border/50 bg-card overflow-hidden',
        className
      )}
    >
      {/* Compact row */}
      <div
        className="flex items-center gap-3 p-3 cursor-pointer hover:bg-muted/50 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        {/* Icon */}
        <div className={clsx('flex-shrink-0', statusColors[toolCall.status])}>
          {toolCall.status === 'running' ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <IconComponent className="w-5 h-5" />
          )}
        </div>

        {/* Name + status */}
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium truncate">{displayName}</div>
        </div>

        {/* Status badge */}
        <Badge className={clsx('text-xs', badgeClasses[toolCall.status])}>
          <StatusIcon className={clsx('w-3 h-3', toolCall.status === 'running' && 'animate-spin')} />
          {getStatusLabel(toolCall.status, isZh)}
        </Badge>

        {/* Duration */}
        <div className="text-xs text-muted-foreground font-mono min-w-[50px] text-right">
          {duration}
        </div>

        {/* Expand indicator */}
        <ChevronDown
          className={clsx(
            'w-4 h-4 text-muted-foreground transition-transform flex-shrink-0',
            isExpanded && 'rotate-180'
          )}
        />
      </div>

      {/* Expanded content */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="overflow-hidden"
          >
            <div className="px-3 pb-3 space-y-3">
              {/* Parameters */}
              <div>
                <div className="text-xs font-semibold mb-1 text-muted-foreground">{t.parameters}</div>
                <pre className="bg-gray-50 dark:bg-gray-900/50 p-3 rounded text-xs font-mono overflow-x-auto max-h-40">
                  {JSON.stringify(toolCall.parameters, null, 2)}
                </pre>
              </div>

              {/* Result */}
              {hasResult && (
                <div>
                  <div className="text-xs font-semibold mb-1 text-muted-foreground">{t.result}</div>
                  {typeof toolCall.result === 'string' ? (
                    <div className="text-sm text-foreground whitespace-pre-wrap">
                      {toolCall.result}
                    </div>
                  ) : typeof toolCall.result === 'object' ? (
                    <pre className="bg-gray-50 dark:bg-gray-900/50 p-3 rounded text-xs font-mono overflow-x-auto max-h-40">
                      {JSON.stringify(toolCall.result, null, 2)}
                    </pre>
                  ) : null}
                  {/* Error result */}
                  {typeof toolCall.result === 'object' &&
                    toolCall.result !== null &&
                    'success' in toolCall.result &&
                    (toolCall.result as { success?: boolean }).success === false && (
                      <div className="text-sm text-destructive mt-1">
                        {(toolCall.result as { error?: string }).error ?? 'Unknown error'}
                      </div>
                    )}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
