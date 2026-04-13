/**
 * ThinkingStatusLine Component
 *
 * Displays Agent thinking status with animated icon, flowing summary text,
 * step progress, duration timer, and expand details button.
 *
 * Part of Agent-Native Chat architecture
 */

import { clsx } from 'clsx';
import { useEffect, useState } from 'react';

/**
 * Thinking status type
 */
export type ThinkingStatus = 'idle' | 'analyzing' | 'planning' | 'executing' | 'synthesizing';

/**
 * Status configuration with icon and color
 */
const STATUS_CONFIG: Record<ThinkingStatus, { icon: string; color: string }> = {
  idle: { icon: '○', color: 'text-gray-400' },
  analyzing: { icon: '◐', color: 'text-blue-500 animate-spin' },
  planning: { icon: '◑', color: 'text-blue-400 animate-pulse' },
  executing: { icon: '◉', color: 'text-blue-600 animate-pulse' },
  synthesizing: { icon: '●', color: 'text-green-500' },
};

/**
 * ThinkingStatusLine props
 */
export interface ThinkingStatusLineProps {
  /** Current thinking status */
  status: ThinkingStatus;
  /** Summary text to display (flows when streaming) */
  summary: string;
  /** Step progress information */
  stepProgress?: { current: number; total: number };
  /** Duration in milliseconds */
  duration_ms?: number;
  /** Whether summary is actively streaming */
  isStreaming: boolean;
  /** Whether expand details button should be shown */
  hasDetails?: boolean;
  /** Callback when expand button is clicked */
  onExpand?: () => void;
}

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
 * ThinkingStatusLine Component
 *
 * Visual elements:
 * 1. Status Icon (dynamic) - different icons and colors per status
 * 2. Summary Text (flowing effect) - current thinking content
 * 3. Step Progress - steps X/Y
 * 4. Duration - elapsed time
 * 5. Expand Button - expand details popup
 */
export function ThinkingStatusLine({
  status,
  summary,
  stepProgress,
  duration_ms,
  isStreaming,
  hasDetails = false,
  onExpand,
}: ThinkingStatusLineProps) {
  const config = STATUS_CONFIG[status];
  const [displayDuration, setDisplayDuration] = useState(duration_ms ?? 0);

  // Update duration display when streaming
  useEffect(() => {
    // Always set the initial duration from props
    setDisplayDuration(duration_ms ?? 0);

    if (!isStreaming || duration_ms === undefined) {
      return;
    }

    // Start counting from provided duration
    const startTime = Date.now() - duration_ms;
    const interval = setInterval(() => {
      setDisplayDuration(Date.now() - startTime);
    }, 100);

    return () => clearInterval(interval);
  }, [isStreaming, duration_ms]);

  return (
    <div
      className={clsx(
        'flex items-center gap-2 px-3 py-1.5 rounded-md',
        'bg-muted/30 border border-muted/50',
        'text-sm transition-all duration-200'
      )}
    >
      {/* Status Icon */}
      <span
        role="status"
        aria-label={`Thinking status: ${status}`}
        className={clsx(
          'flex-shrink-0 text-base leading-none',
          config.color
        )}
      >
        {config.icon}
      </span>

      {/* Summary Text with streaming effect */}
      <span
        className={clsx(
          'flex-1 min-w-0 truncate',
          isStreaming && 'animate-pulse'
        )}
      >
        {summary}
      </span>

      {/* Step Progress */}
      {stepProgress && (
        <span className="flex-shrink-0 text-xs text-muted-foreground tabular-nums">
          {stepProgress.current}/{stepProgress.total}
        </span>
      )}

      {/* Duration */}
      {displayDuration > 0 && (
        <span className="flex-shrink-0 text-xs text-muted-foreground tabular-nums">
          {formatDuration(displayDuration)}
        </span>
      )}

      {/* Expand Button */}
      {hasDetails && onExpand && (
        <button
          type="button"
          aria-label="Expand details"
          onClick={onExpand}
          className={clsx(
            'flex-shrink-0 p-1 rounded hover:bg-muted/50',
            'text-muted-foreground hover:text-foreground',
            'transition-colors duration-150'
          )}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
      )}
    </div>
  );
}

export type { ThinkingStatusLineProps as ThinkingStatusLinePropsType };