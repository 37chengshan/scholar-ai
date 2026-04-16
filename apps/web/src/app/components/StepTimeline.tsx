/**
 * StepTimeline Component
 *
 * Vertical timeline visualization for execution steps.
 * Shows status indicators with connecting lines.
 *
 * Part of Agent-Native Chat (Task 3.3)
 */

import {
  Loader2,
  CheckCircle2,
  XCircle,
  Circle,
  Brain,
  Wrench,
} from 'lucide-react';
import { clsx } from 'clsx';
import { useLanguage } from '../contexts/LanguageContext';

/**
 * Step status type
 */
export type StepStatus = 'pending' | 'running' | 'success' | 'error';

/**
 * Single execution step
 */
export interface Step {
  name: string;
  status: StepStatus;
  duration?: number;
  thought?: string;
  timestamp?: number;
}

/**
 * StepTimeline props
 */
export interface StepTimelineProps {
  steps: Step[];
  className?: string;
}

/**
 * Get icon for step type
 */
function getStepIcon(name: string) {
  const lowerName = name.toLowerCase();
  if (lowerName.includes('think') || lowerName.includes('analyze') || lowerName.includes('plan')) {
    return Brain;
  }
  return Wrench;
}

/**
 * Get status color class
 */
function getStatusColor(status: StepStatus): string {
  const colors: Record<StepStatus, string> = {
    pending: 'text-muted-foreground',
    running: 'text-primary',
    success: 'text-green-600',
    error: 'text-destructive',
  };
  return colors[status];
}

/**
 * Get background color for status indicator
 */
function getStatusBgColor(status: StepStatus): string {
  const colors: Record<StepStatus, string> = {
    pending: 'bg-muted',
    running: 'bg-primary/20 ring-2 ring-primary ring-offset-2',
    success: 'bg-green-100',
    error: 'bg-destructive/10',
  };
  return colors[status];
}

/**
 * Get status icon component
 */
function getStatusIcon(status: StepStatus) {
  const icons: Record<StepStatus, React.ElementType> = {
    pending: Circle,
    running: Loader2,
    success: CheckCircle2,
    error: XCircle,
  };
  return icons[status];
}

/**
 * Format duration
 */
function formatDuration(ms: number, isZh: boolean): string {
  if (ms < 1000) return `${ms}ms`;
  const seconds = ms / 1000;
  if (seconds < 60) return `${seconds.toFixed(1)}${isZh ? '秒' : 's'}`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}${isZh ? '分' : 'm'} ${remainingSeconds.toFixed(0)}${isZh ? '秒' : 's'}`;
}

/**
 * StepTimeline Component
 *
 * Renders a vertical timeline with status indicators.
 */
export function StepTimeline({ steps, className }: StepTimelineProps) {
  const { language } = useLanguage();
  const isZh = language === 'zh';

  if (steps.length === 0) {
    return (
      <div className={clsx('text-center py-4 text-muted-foreground', className)}>
        <Circle className="w-6 h-6 mx-auto mb-2 opacity-30" />
        <p className="text-xs">
          {isZh ? '暂无执行步骤' : 'No execution steps'}
        </p>
      </div>
    );
  }

  return (
    <div className={clsx('space-y-0', className)}>
      {steps.map((step, idx) => {
        const StepIcon = getStepIcon(step.name);
        const StatusIcon = getStatusIcon(step.status);
        const isLast = idx === steps.length - 1;
        const isCompleted = step.status === 'success';
        const isRunning = step.status === 'running';
        const isError = step.status === 'error';

        return (
          <div key={idx} className="flex gap-3">
            {/* Timeline connector */}
            <div className="flex flex-col items-center">
              <div
                className={clsx(
                  'w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0',
                  getStatusBgColor(step.status)
                )}
              >
                {isRunning ? (
                  <Loader2 className="w-3.5 h-3.5 text-primary animate-spin" />
                ) : isCompleted ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-green-600" />
                ) : isError ? (
                  <XCircle className="w-3.5 h-3.5 text-destructive" />
                ) : (
                  <StepIcon className="w-3.5 h-3.5 text-muted-foreground" />
                )}
              </div>
              {/* Connector line */}
              {!isLast && (
                <div
                  className={clsx(
                    'w-0.5 flex-1 min-h-[24px]',
                    isCompleted ? 'bg-green-200' : 'bg-border/50'
                  )}
                />
              )}
            </div>

            {/* Step content */}
            <div className="flex-1 pb-3">
              <div
                className={clsx(
                  'text-sm font-medium',
                  getStatusColor(step.status)
                )}
              >
                {step.name}
              </div>

              {/* Duration */}
              {step.duration !== undefined && step.duration > 0 && (
                <div className="text-xs text-muted-foreground mt-0.5 font-mono">
                  {formatDuration(step.duration, isZh)}
                </div>
              )}

              {/* Thought preview */}
              {step.thought && (
                <div className="text-xs text-muted-foreground mt-1 line-clamp-2">
                  {step.thought}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export type { StepTimelineProps as StepTimelinePropsType };