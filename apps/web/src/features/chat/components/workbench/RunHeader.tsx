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
  gray: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
  blue: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
  yellow: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
  green: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
  red: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
  orange: 'bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300',
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
      className="flex items-center gap-3 px-4 py-2 border-b border-gray-100 dark:border-gray-800 bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm"
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
        <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
          <div className="w-20 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-blue-500 rounded-full"
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
        <span className="text-xs text-gray-400 dark:text-gray-500 truncate max-w-[200px]">
          {run.objective}
        </span>
      )}
    </motion.div>
  );
}
