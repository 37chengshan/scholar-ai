/**
 * ExecutionTimeline — Displays the step-by-step run progress.
 *
 * Per 战役 B WP4: Execution timeline replaces the old tool timeline.
 */

import { motion, AnimatePresence } from 'motion/react';
import { memo, useMemo } from 'react';
import type { RunTimelineItem } from '@/features/chat/types/run';

interface ExecutionTimelineProps {
  items: RunTimelineItem[];
  collapsed?: boolean;
}

const TYPE_ICONS: Record<string, string> = {
  phase: '◆',
  step: '▸',
  tool: '⚙',
  confirmation: '⚠',
  done: '✓',
  error: '✕',
  recovery: '↺',
};

const STATUS_COLORS: Record<string, string> = {
  running: 'text-blue-500',
  completed: 'text-emerald-500',
  failed: 'text-red-500',
  waiting: 'text-amber-500',
  success: 'text-emerald-500',
};

function ExecutionTimelineBase({ items, collapsed = false }: ExecutionTimelineProps) {
  if (items.length === 0) return null;

  const visibleItems = useMemo(() => (collapsed ? items.slice(-5) : items), [collapsed, items]);

  if (collapsed) {
    return (
      <div className="px-3 py-2">
        {visibleItems.map((item) => {
          const icon = TYPE_ICONS[item.type] || '•';
          const colorClass = STATUS_COLORS[item.status || ''] || 'text-gray-400';

          return (
            <div key={item.id} className="flex items-center gap-2 py-0.5 text-xs">
              <span className={`font-mono ${colorClass}`}>{icon}</span>
              <span className="text-gray-600 dark:text-gray-400 truncate">{item.label}</span>
              {item.status === 'running' && (
                <span className="ml-auto">
                  <span className="animate-pulse text-blue-400">●</span>
                </span>
              )}
            </div>
          );
        })}
        {items.length > 5 && (
          <div className="text-xs text-gray-400 mt-1">
            +{items.length - 5} more steps
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="px-3 py-2">
      <AnimatePresence mode="popLayout">
        {visibleItems.map((item) => {
          const icon = TYPE_ICONS[item.type] || '•';
          const colorClass = STATUS_COLORS[item.status || ''] || 'text-gray-400';

          return (
            <motion.div
              key={item.id}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0 }}
              className="flex items-center gap-2 py-0.5 text-xs"
            >
              <span className={`font-mono ${colorClass}`}>{icon}</span>
              <span className="text-gray-600 dark:text-gray-400 truncate">{item.label}</span>
              {item.status === 'running' && (
                <span className="ml-auto">
                  <span className="animate-pulse text-blue-400">●</span>
                </span>
              )}
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}

export const ExecutionTimeline = memo(ExecutionTimelineBase);
