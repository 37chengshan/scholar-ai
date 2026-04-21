/**
 * EvidencePanel — Displays collected evidence and citations for the run.
 *
 * Per 战役 B WP4: Evidence panel replaces the old citations panel.
 */

import { motion, AnimatePresence } from 'motion/react';
import type { RunEvidence } from '@/features/chat/types/run';

interface EvidencePanelProps {
  evidence: RunEvidence[];
  maxVisible?: number;
}

function ConsistencyDot({ value }: { value?: number }) {
  if (value == null) return null;
  const color = value >= 0.8 ? 'bg-emerald-400' : value >= 0.5 ? 'bg-amber-400' : 'bg-red-400';
  return (
    <span className={`inline-block w-2 h-2 rounded-full ${color}`} title={`Consistency: ${(value * 100).toFixed(0)}%`} />
  );
}

export function EvidencePanel({ evidence, maxVisible = 10 }: EvidencePanelProps) {
  if (evidence.length === 0) return null;

  const visible = evidence.slice(0, maxVisible);

  return (
    <div className="space-y-1 px-3 py-2">
      <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
        证据来源 ({evidence.length})
      </div>
      <AnimatePresence mode="popLayout">
        {visible.map((e, i) => (
          <motion.div
            key={e.sourceId || i}
            initial={{ opacity: 0, x: -4 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex items-start gap-2 py-1 text-xs border-l-2 border-blue-200 dark:border-blue-800 pl-2"
          >
            <div className="flex-1 min-w-0">
              <div className="font-medium text-gray-700 dark:text-gray-300 truncate flex items-center gap-1.5">
                {e.title}
                <ConsistencyDot value={e.consistency} />
              </div>
              {e.textPreview && (
                <div className="text-gray-500 dark:text-gray-400 line-clamp-2 mt-0.5">
                  {e.textPreview}
                </div>
              )}
              {e.pageNum != null && (
                <span className="text-gray-400 text-[10px]">p.{e.pageNum}</span>
              )}
            </div>
            {e.relevance != null && (
              <span className="text-[10px] text-gray-400 whitespace-nowrap">
                {(e.relevance * 100).toFixed(0)}%
              </span>
            )}
          </motion.div>
        ))}
      </AnimatePresence>
      {evidence.length > maxVisible && (
        <div className="text-xs text-gray-400 mt-1">
          +{evidence.length - maxVisible} more
        </div>
      )}
    </div>
  );
}
