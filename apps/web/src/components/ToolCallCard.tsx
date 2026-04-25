/**
 * Deprecated compatibility component.
 *
 * Keep the legacy API stable for older callers and tests.
 * New product work should land in `src/app/components/ToolCallCard.tsx`.
 */

import { clsx } from 'clsx';

export type ToolStatus = 'pending' | 'running' | 'success' | 'error';

const TOOL_DISPLAY: Record<string, { name: string; icon: string }> = {
  rag_search: { name: 'RAG搜索', icon: '🔍' },
  external_search: { name: '外部搜索', icon: '🌐' },
  read_paper: { name: '阅读论文', icon: '📄' },
  list_papers: { name: '论文列表', icon: '📋' },
  create_note: { name: '创建笔记', icon: '📝' },
  extract_references: { name: '提取引用', icon: '📑' },
};

const STATUS_CONFIG: Record<ToolStatus, { indicator: string; color: string }> = {
  pending: { indicator: '○', color: 'text-gray-400 pending' },
  running: { indicator: '◐', color: 'text-blue-500 animate-spin running' },
  success: { indicator: '●', color: 'text-green-500 success' },
  error: { indicator: '✕', color: 'text-red-500 error' },
};

export interface ToolCallCardProps {
  tool: string;
  parameters: Record<string, unknown>;
  status: ToolStatus;
  result?: unknown;
  error?: string;
  duration?: number;
  usedFallback?: boolean;
  fallbackTool?: string;
}

function formatDuration(ms: number): string {
  const seconds = ms / 1000;
  if (seconds < 60) {
    return `${seconds.toFixed(2)}s`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.floor(seconds - minutes * 60);
  return `${minutes}m ${remainingSeconds}s`;
}

function formatParameters(params: Record<string, unknown>): string {
  const entries = Object.entries(params);
  if (entries.length === 0) return '';

  return entries
    .map(([key, value]) => {
      const displayValue = typeof value === 'string' ? value : JSON.stringify(value);
      const truncated = displayValue.length > 20 ? `${displayValue.slice(0, 20)}...` : displayValue;
      return `${key}: ${truncated}`;
    })
    .join(', ');
}

function formatResultPreview(result: unknown): string {
  if (result === null || result === undefined) return '';

  if (typeof result === 'object') {
    const obj = result as Record<string, unknown>;
    if ('total' in obj) {
      return `total: ${obj.total}`;
    }
    if ('papers' in obj && Array.isArray(obj.papers)) {
      return `${obj.papers.length} papers`;
    }
    if ('count' in obj) {
      return `count: ${obj.count}`;
    }
    const keys = Object.keys(obj);
    return keys.length > 0 ? keys.join(', ') : '';
  }

  return String(result).slice(0, 30);
}

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
      <span className="flex-shrink-0">{toolConfig.icon}</span>
      <span className="flex-shrink-0 font-medium">{toolConfig.name}</span>

      {paramsDisplay && (
        <span className="flex-1 min-w-0 text-muted-foreground truncate">
          [{paramsDisplay}]
        </span>
      )}

      <span
        role="status"
        aria-label={`Tool status: ${status}`}
        className={clsx('flex-shrink-0', statusConfig.color)}
      >
        {statusConfig.indicator}
      </span>

      {duration !== undefined && duration > 0 && (
        <span className="flex-shrink-0 text-muted-foreground tabular-nums">
          {formatDuration(duration)}
        </span>
      )}

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

      {resultPreview && (
        <span className="flex-shrink-0 text-green-600 dark:text-green-400">
          → {resultPreview}
        </span>
      )}

      {status === 'error' && error && (
        <span className="flex-shrink-0 text-red-600 dark:text-red-400 truncate max-w-[150px]">
          {error}
        </span>
      )}
    </div>
  );
}

export type { ToolCallCardProps as ToolCallCardPropsType };
