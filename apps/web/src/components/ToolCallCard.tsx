/**
 * ToolCallCard Component
 *
 * Displays tool execution status with name, icon, parameters, result preview,
 * duration, and fallback indicator.
 *
 * Part of Agent-Native Chat architecture
 */

import { clsx } from 'clsx';

/**
 * Tool execution status
 */
export type ToolStatus = 'pending' | 'running' | 'success' | 'error';

/**
 * Tool display configuration
 */
const TOOL_DISPLAY: Record<string, { name: string; icon: string }> = {
  rag_search: { name: 'RAG搜索', icon: '🔍' },
  external_search: { name: '外部搜索', icon: '🌐' },
  read_paper: { name: '阅读论文', icon: '📄' },
  list_papers: { name: '论文列表', icon: '📋' },
  create_note: { name: '创建笔记', icon: '📝' },
  extract_references: { name: '提取引用', icon: '📑' },
};

/**
 * Status configuration with indicator and color
 */
const STATUS_CONFIG: Record<ToolStatus, { indicator: string; color: string }> = {
  pending: { indicator: '○', color: 'text-gray-400' },
  running: { indicator: '◐', color: 'text-blue-500 animate-spin' },
  success: { indicator: '●', color: 'text-green-500' },
  error: { indicator: '✕', color: 'text-red-500' },
};

/**
 * ToolCallCard props
 */
export interface ToolCallCardProps {
  /** Tool name identifier */
  tool: string;
  /** Tool parameters */
  parameters: Record<string, unknown>;
  /** Execution status */
  status: ToolStatus;
  /** Result data (when status is success) */
  result?: unknown;
  /** Error message (when status is error) */
  error?: string;
  /** Duration in milliseconds */
  duration?: number;
  /** Whether fallback tool was used */
  usedFallback?: boolean;
  /** The fallback tool that was used */
  fallbackTool?: string;
}

/**
 * Format duration in milliseconds to human-readable string
 */
function formatDuration(ms: number): string {
  const seconds = ms / 1000;
  if (seconds < 60) {
    return `${seconds.toFixed(2)}s`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.floor(seconds - minutes * 60);
  return `${minutes}m ${remainingSeconds}s`;
}

/**
 * Format parameters as compact display
 */
function formatParameters(params: Record<string, unknown>): string {
  const entries = Object.entries(params);
  if (entries.length === 0) return '';

  return entries
    .map(([key, value]) => {
      const displayValue =
        typeof value === 'string' ? value : JSON.stringify(value);
      const truncated =
        displayValue.length > 20 ? `${displayValue.slice(0, 20)}...` : displayValue;
      return `${key}: ${truncated}`;
    })
    .join(', ');
}

/**
 * Format result preview
 */
function formatResultPreview(result: unknown): string {
  if (result === null || result === undefined) return '';

  if (typeof result === 'object') {
    const obj = result as Record<string, unknown>;
    // Show key summary metrics
    if ('total' in obj) {
      return `total: ${obj.total}`;
    }
    if ('papers' in obj && Array.isArray(obj.papers)) {
      return `${obj.papers.length} papers`;
    }
    if ('count' in obj) {
      return `count: ${obj.count}`;
    }
    // Fallback: show keys
    const keys = Object.keys(obj);
    return keys.length > 0 ? keys.join(', ') : '';
  }

  return String(result).slice(0, 30);
}

/**
 * ToolCallCard Component
 *
 * Visual elements:
 * 1. Tool Name + Icon - from TOOL_DISPLAY config
 * 2. Parameters Display - compact format
 * 3. Status Indicator - color-coded
 * 4. Duration Timer - when available
 * 5. Fallback Indicator - when used
 * 6. Result Preview - when success
 * 7. Error Message - when error
 */
export function ToolCallCard({
  tool,
  parameters,
  status,
  result,
  error,
  duration,
  usedFallback,
  fallbackTool,
}: ToolCallCardProps) {
  const toolConfig = TOOL_DISPLAY[tool] || { name: tool, icon: '⚙' };
  const statusConfig = STATUS_CONFIG[status];
  const paramsDisplay = formatParameters(parameters);
  const resultPreview = status === 'success' ? formatResultPreview(result) : '';

  return (
    <div
      data-testid="tool-call-card"
      className={clsx(
        'flex items-center gap-2 px-2 py-1.5 rounded-md',
        'bg-muted/30 border border-muted/50',
        'text-xs transition-all duration-200'
      )}
    >
      {/* Tool Icon */}
      <span className="flex-shrink-0">{toolConfig.icon}</span>

      {/* Tool Name */}
      <span className="flex-shrink-0 font-medium">{toolConfig.name}</span>

      {/* Parameters */}
      {paramsDisplay && (
        <span className="flex-1 min-w-0 text-muted-foreground truncate">
          [{paramsDisplay}]
        </span>
      )}

      {/* Status Indicator */}
      <span
        role="status"
        aria-label={`Tool status: ${status}`}
        className={clsx('flex-shrink-0', statusConfig.color)}
      >
        {statusConfig.indicator}
      </span>

      {/* Duration */}
      {duration !== undefined && duration > 0 && (
        <span className="flex-shrink-0 text-muted-foreground tabular-nums">
          {formatDuration(duration)}
        </span>
      )}

      {/* Fallback Indicator */}
      {usedFallback && fallbackTool && (
        <span
          className={clsx(
            'flex-shrink-0 px-1 rounded',
            'bg-yellow-100 text-yellow-700',
            'dark:bg-yellow-900/30 dark:text-yellow-500'
          )}
        >
          备用: {TOOL_DISPLAY[fallbackTool]?.name || fallbackTool}
        </span>
      )}

      {/* Result Preview */}
      {resultPreview && (
        <span className="flex-shrink-0 text-green-600 dark:text-green-400">
          → {resultPreview}
        </span>
      )}

      {/* Error Message */}
      {status === 'error' && error && (
        <span className="flex-shrink-0 text-red-600 dark:text-red-400 truncate max-w-[150px]">
          {error}
        </span>
      )}
    </div>
  );
}

export type { ToolCallCardProps as ToolCallCardPropsType };