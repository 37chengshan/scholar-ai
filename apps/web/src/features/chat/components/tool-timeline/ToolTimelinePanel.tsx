/**
 * ToolTimelinePanel - Visual stepper for tool call timeline
 *
 * Phase 5.0-6: Upgraded to design system v2 tokens.
 * Stepper visual (dot + line + dot), semantic color states,
 * expandable error details.
 */

import { useState } from 'react';
import { ChevronDown, ChevronRight, Wrench, CheckCircle2, XCircle, Loader2, Circle } from 'lucide-react';
import { clsx } from 'clsx';
import type { ToolTimelineItem } from '@/features/chat/components/workspaceTypes';

interface ToolTimelinePanelProps {
  visible: boolean;
  timeline: ToolTimelineItem[];
  isZh?: boolean;
}

type StepStatus = 'pending' | 'running' | 'success' | 'error';

function getStepStatus(item: ToolTimelineItem): StepStatus {
  if (item.status === 'success') return 'success';
  if (item.status === 'error') return 'error';
  if (item.status === 'running') return 'running';
  return 'pending';
}

function StepStatusIcon({ status }: { status: StepStatus }) {
  switch (status) {
    case 'success':
      return <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />;
    case 'error':
      return <XCircle className="w-3.5 h-3.5 text-red-500" />;
    case 'running':
      return <Loader2 className="w-3.5 h-3.5 text-primary animate-spin" />;
    case 'pending':
    default:
      return <Circle className="w-3.5 h-3.5 text-muted-foreground/40" />;
  }
}

function getStatusColor(status: StepStatus): string {
  switch (status) {
    case 'success':
      return 'border-emerald-500/30 bg-emerald-500/5';
    case 'error':
      return 'border-red-500/30 bg-red-500/5';
    case 'running':
      return 'border-primary/30 bg-primary/5';
    case 'pending':
    default:
      return 'border-border/40 bg-muted/20';
  }
}

interface StepItemProps {
  item: ToolTimelineItem;
  isLast: boolean;
  isZh: boolean;
}

function StepItem({ item, isLast, isZh }: StepItemProps) {
  const [errorExpanded, setErrorExpanded] = useState(false);
  const status = getStepStatus(item);
  const hasError = status === 'error';

  return (
    <div className="flex gap-2">
      {/* Stepper: dot + line */}
      <div className="flex flex-col items-center">
        <StepStatusIcon status={status} />
        {!isLast && (
          <div className={clsx(
            'w-px flex-1 min-h-[16px] mt-1',
            status === 'success' ? 'bg-emerald-500/30' : 'bg-border/40',
          )} />
        )}
      </div>

      {/* Content */}
      <div className={clsx(
        'flex-1 rounded-md border px-2.5 py-1.5 mb-2 transition-colors duration-[var(--duration-fast)]',
        getStatusColor(status),
      )}>
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-medium text-foreground/80">{item.label || item.tool}</span>
          {item.duration && (
            <span className="text-[10px] text-muted-foreground tabular-nums">
              {item.duration >= 1000 ? `${(item.duration / 1000).toFixed(1)}s` : `${item.duration}ms`}
            </span>
          )}
        </div>

        {item.summary && !hasError && (
          <p className="text-[11px] text-foreground/60 mt-0.5 line-clamp-2">{item.summary}</p>
        )}

        {/* Expandable error details */}
        {hasError && (
          <div className="mt-1">
            <button
              type="button"
              onClick={() => setErrorExpanded(v => !v)}
              className="flex items-center gap-1 text-[10px] text-red-600 hover:text-red-700 transition-colors"
            >
              {errorExpanded
                ? <ChevronDown className="w-3 h-3" />
                : <ChevronRight className="w-3 h-3" />
              }
              {isZh ? '查看错误详情' : 'View error details'}
            </button>
            {errorExpanded && (
              <div className="mt-1 rounded bg-red-500/5 border border-red-500/20 px-2 py-1.5 text-[10px] text-red-700 font-mono">
                {item.summary || (isZh ? '未知错误' : 'Unknown error')}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export function ToolTimelinePanel({ visible, timeline, isZh = true }: ToolTimelinePanelProps) {
  const [expanded, setExpanded] = useState(false);

  if (!visible || timeline.length === 0) {
    return null;
  }

  const completedCount = timeline.filter(t => t.status === 'success' || t.status === 'error').length;
  const errorCount = timeline.filter(t => t.status === 'error').length;

  return (
    <div className="w-full">
      {/* Collapsed summary row */}
      <button
        type="button"
        onClick={() => setExpanded(v => !v)}
        className="flex items-center gap-1.5 text-[11px] text-muted-foreground hover:text-foreground transition-colors duration-[var(--duration-fast)] py-1 group"
      >
        {expanded
          ? <ChevronDown className="w-3 h-3" />
          : <ChevronRight className="w-3 h-3" />
        }
        <Wrench className="w-3 h-3 text-muted-foreground/60" />
        <span>
          {completedCount > 0
            ? (isZh ? `已调用 ${timeline.length} 个工具` : `Called ${timeline.length} tool${timeline.length > 1 ? 's' : ''}`)
            : (isZh ? `调用 ${timeline.length} 个工具中...` : `Calling ${timeline.length} tool${timeline.length > 1 ? 's' : ''}...`)
          }
        </span>
        {errorCount > 0 && (
          <span className="text-[10px] text-red-500 bg-red-500/10 rounded-full px-1.5 py-0.5">
            {errorCount} {isZh ? '个错误' : 'error' + (errorCount > 1 ? 's' : '')}
          </span>
        )}
      </button>

      {/* Expanded stepper */}
      {expanded && (
        <div className="mt-1 ml-1">
          {timeline.map((item, index) => (
            <StepItem
              key={item.id}
              item={item}
              isLast={index === timeline.length - 1}
              isZh={isZh}
            />
          ))}
        </div>
      )}
    </div>
  );
}
