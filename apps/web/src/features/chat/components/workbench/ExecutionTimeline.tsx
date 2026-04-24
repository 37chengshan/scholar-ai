/**
 * ExecutionTimeline — Displays the step-by-step run progress.
 *
 * Per 战役 B WP4: Execution timeline replaces the old tool timeline.
 */

import { motion, AnimatePresence } from 'motion/react';
import { memo, useMemo } from 'react';
import { AlertCircle, CheckCircle2, Circle, Cog, RotateCcw, Route, Timer } from 'lucide-react';
import type { RunTimelineItem } from '@/features/chat/types/run';

interface ExecutionTimelineProps {
  items: RunTimelineItem[];
  collapsed?: boolean;
}

const TYPE_ICON: Record<string, typeof Circle> = {
  phase: Route,
  step: Circle,
  tool: Cog,
  confirmation: AlertCircle,
  done: CheckCircle2,
  error: AlertCircle,
  recovery: RotateCcw,
};

const STATUS_CLASS: Record<string, string> = {
  running: 'text-primary',
  completed: 'text-emerald-600',
  failed: 'text-destructive',
  waiting: 'text-secondary',
  success: 'text-emerald-600',
};

function ExecutionTimelineBase({ items, collapsed = false }: ExecutionTimelineProps) {
  if (items.length === 0) return null;

  const visibleItems = useMemo(() => (collapsed ? items.slice(-5) : items), [collapsed, items]);

  return (
    <div className="space-y-1">
      <AnimatePresence mode="popLayout">
        {visibleItems.map((item) => {
          const Icon = TYPE_ICON[item.type] || Circle;
          const colorClass = STATUS_CLASS[item.status || ''] || 'text-muted-foreground';

          return (
            <motion.div
              key={item.id}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0 }}
              className="flex items-center gap-2 rounded-sm px-1 py-1 text-xs"
            >
              <Icon className={`h-3.5 w-3.5 ${colorClass}`} />
              <span className="truncate text-foreground/82">{item.label}</span>
              {item.status === 'running' ? (
                <Timer className="ml-auto h-3.5 w-3.5 animate-pulse text-primary/80" />
              ) : null}
            </motion.div>
          );
        })}
      </AnimatePresence>
      {collapsed && items.length > 5 ? (
        <div className="text-xs text-muted-foreground">+{items.length - 5} more steps</div>
      ) : null}
    </div>
  );
}

export const ExecutionTimeline = memo(ExecutionTimelineBase);
