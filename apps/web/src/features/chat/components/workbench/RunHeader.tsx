/**
 * RunHeader — Shows current Run phase, progress, and badge.
 *
 * Per 战役 B WP4: Lightweight header inside the chat area.
 */

import { motion } from 'motion/react';
import type { AgentRun } from '@/features/chat/types/run';
import { resolveRunBadge, resolveStepProgress } from '@/features/chat/resolvers/runResolvers';

interface RunHeaderProps {
  run: AgentRun;
}

const BADGE_COLORS: Record<string, string> = {
  gray: 'bg-muted text-muted-foreground',
  blue: 'bg-primary/12 text-primary',
  yellow: 'bg-secondary/20 text-secondary-foreground',
  green: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
  red: 'bg-destructive/15 text-destructive',
  orange: 'bg-accent text-accent-foreground',
};

export function RunHeader({ run }: RunHeaderProps) {
  if (run.status === 'idle') return null;

  const badge = resolveRunBadge(run);
  const progress = resolveStepProgress(run);
  const badgeClass = BADGE_COLORS[badge.color] || BADGE_COLORS.gray;

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-center gap-3 border-b border-border/40 bg-background/70 px-4 py-2 backdrop-blur-sm"
    >
      {/* Phase badge */}
      <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium ${badgeClass}`}>
        {badge.pulse && (
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-current opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-current" />
          </span>
        )}
        {badge.label}
      </span>

      {/* Step progress */}
      {progress.total > 0 && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <div className="h-1.5 w-20 overflow-hidden rounded-full bg-muted">
            <motion.div
              className="h-full rounded-full bg-primary"
              initial={{ width: 0 }}
              animate={{ width: `${progress.percentage}%` }}
              transition={{ duration: 0.3 }}
            />
          </div>
          <span>{progress.completed}/{progress.total}</span>
        </div>
      )}

      {/* Objective */}
      {run.objective && (
        <span className="max-w-[200px] truncate text-xs text-muted-foreground">
          {run.objective}
        </span>
      )}
    </motion.div>
  );
}
