/**
 * RecoveryBanner — Shows available recovery actions (retry/cancel/confirm).
 *
 * Per 战役 B WP4: Recovery actions are visible when run is recoverable.
 */

import { motion } from 'motion/react';
import type { PendingAction } from '@/features/chat/types/run';
import { resolveRecoveryUI } from '@/features/chat/resolvers/runResolvers';

interface RecoveryBannerProps {
  actions: PendingAction[];
  onAction: (actionType: string) => void;
}

const VARIANT_CLASSES = {
  primary: 'bg-blue-600 hover:bg-blue-700 text-white',
  secondary: 'bg-gray-200 hover:bg-gray-300 text-gray-700 dark:bg-gray-700 dark:hover:bg-gray-600 dark:text-gray-200',
  danger: 'bg-red-600 hover:bg-red-700 text-white',
};

export function RecoveryBanner({ actions, onAction }: RecoveryBannerProps) {
  const ui = resolveRecoveryUI(actions);
  if (!ui.visible) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-center justify-center gap-2 px-4 py-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50"
    >
      <span className="text-xs text-gray-500 dark:text-gray-400 mr-2">
        操作可用:
      </span>
      {ui.actions.map((action) => (
        <button
          key={action.id}
          onClick={() => onAction(action.id)}
          className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${VARIANT_CLASSES[action.variant]}`}
        >
          {action.label}
        </button>
      ))}
    </motion.div>
  );
}
