/**
 * Deprecated compatibility component.
 *
 * Keep the legacy API stable for older callers and tests.
 * New product work should land in `src/app/components/StepTimeline.tsx`.
 */

import { clsx } from 'clsx';

export type StepStatus = 'pending' | 'running' | 'success' | 'error';

export interface Step {
  name: string;
  status: StepStatus;
  duration?: number;
  thought?: string;
}

export interface StepTimelineProps {
  steps: Step[];
  currentStep?: number;
}

const STATUS_CONFIG: Record<Step['status'], { icon: string; colorClass: string }> = {
  pending: { icon: '○', colorClass: 'text-gray-400 pending muted' },
  running: { icon: '◐', colorClass: 'text-blue-500 animate-pulse running' },
  success: { icon: '●', colorClass: 'text-green-500 success completed' },
  error: { icon: '✕', colorClass: 'text-red-500 error failed' },
};

const MAX_THOUGHT_LENGTH = 80;

function formatDuration(ms: number): string {
  const seconds = ms / 1000;
  if (seconds < 60) {
    return `${seconds.toFixed(1)}s`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds - minutes * 60;
  return `${minutes}m ${remainingSeconds.toFixed(0)}s`;
}

function truncateThought(thought: string): string {
  if (thought.length <= MAX_THOUGHT_LENGTH) {
    return thought;
  }
  return thought.slice(0, MAX_THOUGHT_LENGTH) + '...';
}

export function StepTimeline({ steps, currentStep }: StepTimelineProps) {
  if (steps.length === 0) {
    return null;
  }

  return (
    <div data-testid="step-timeline" className={clsx('flex flex-col gap-2', 'timeline-container')}>
      {steps.map((step, index) => {
        const config = STATUS_CONFIG[step.status];
        const isCurrent = index === currentStep;
        const isRunning = step.status === 'running';

        return (
          <div
            key={`${step.name}-${index}`}
            className={clsx(
              'flex items-start gap-3 px-3 py-2 rounded-md',
              'border border-muted/50 bg-muted/20',
              'transition-all duration-200',
              isCurrent && 'bg-muted/40 border-muted current active highlight',
              isRunning && 'animate-pulse running-step'
            )}
          >
            <span
              role="status"
              aria-label={`Step status: ${step.status}`}
              className={clsx('flex-shrink-0 text-base leading-none mt-0.5', config.colorClass)}
            >
              {config.icon}
            </span>

            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-foreground truncate">{step.name}</span>
                {step.duration !== undefined && step.duration > 0 && (
                  <span className="flex-shrink-0 text-xs text-muted-foreground tabular-nums">
                    {formatDuration(step.duration)}
                  </span>
                )}
              </div>

              {step.thought && (
                <p className="mt-1 text-xs text-muted-foreground line-clamp-2">
                  {truncateThought(step.thought)}
                </p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export type { StepTimelineProps as StepTimelinePropsType };
