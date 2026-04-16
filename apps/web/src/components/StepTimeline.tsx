/**
 * StepTimeline Component
 *
 * Visualizes Agent execution steps with status icons, duration,
 * and thought preview. Part of Agent-Native Chat architecture.
 *
 * Features:
 * - Status icons: pending (gray), running (blue pulse), success (green), error (red)
 * - Duration display for completed/running steps
 * - Thought preview with truncation
 * - Vertical timeline layout
 */

import { clsx } from 'clsx';

/**
 * Single step in the execution timeline
 */
export interface Step {
  /** Step name/label */
  name: string;
  /** Current execution status */
  status: 'pending' | 'running' | 'success' | 'error';
  /** Execution duration in milliseconds */
  duration?: number;
  /** Agent's thought/reasoning for this step */
  thought?: string;
}

/**
 * StepTimeline props
 */
export interface StepTimelineProps {
  /** Array of execution steps */
  steps: Step[];
  /** Index of currently executing step (optional) */
  currentStep?: number;
}

/**
 * Status configuration with icon and color classes
 */
const STATUS_CONFIG: Record<Step['status'], { icon: string; colorClass: string }> = {
  pending: { icon: '○', colorClass: 'text-gray-400' },
  running: { icon: '◐', colorClass: 'text-blue-500 animate-pulse' },
  success: { icon: '●', colorClass: 'text-green-500' },
  error: { icon: '✕', colorClass: 'text-red-500' },
};

/**
 * Maximum characters for thought preview
 */
const MAX_THOUGHT_LENGTH = 80;

/**
 * Format duration in milliseconds to human-readable string
 */
function formatDuration(ms: number): string {
  const seconds = ms / 1000;
  if (seconds < 60) {
    return `${seconds.toFixed(1)}s`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds - minutes * 60;
  return `${minutes}m ${remainingSeconds.toFixed(0)}s`;
}

/**
 * Truncate thought text to max length
 */
function truncateThought(thought: string): string {
  if (thought.length <= MAX_THOUGHT_LENGTH) {
    return thought;
  }
  return thought.slice(0, MAX_THOUGHT_LENGTH) + '...';
}

/**
 * StepTimeline Component
 *
 * Renders a vertical timeline of execution steps with:
 * 1. Dynamic status icons
 * 2. Step names
 * 3. Duration (when available)
 * 4. Thought preview (when available)
 */
export function StepTimeline({ steps, currentStep }: StepTimelineProps) {
  // Empty state
  if (steps.length === 0) {
    return null;
  }

  return (
    <div
      data-testid="step-timeline"
      className={clsx('flex flex-col gap-2', 'timeline-container')}
    >
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
              // Highlight current step
              isCurrent && 'bg-muted/40 border-muted',
              // Running animation
              isRunning && 'animate-pulse running-step'
            )}
          >
            {/* Status Icon */}
            <span
              role="status"
              aria-label={`Step status: ${step.status}`}
              className={clsx(
                'flex-shrink-0 text-base leading-none mt-0.5',
                config.colorClass
              )}
            >
              {config.icon}
            </span>

            {/* Step Content */}
            <div className="flex-1 min-w-0">
              {/* Step Name */}
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-foreground truncate">
                  {step.name}
                </span>

                {/* Duration */}
                {step.duration !== undefined && step.duration > 0 && (
                  <span className="flex-shrink-0 text-xs text-muted-foreground tabular-nums">
                    {formatDuration(step.duration)}
                  </span>
                )}
              </div>

              {/* Thought Preview */}
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