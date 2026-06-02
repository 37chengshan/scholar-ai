/**
 * ReasoningPanel - Displays thinking/reasoning steps
 *
 * Phase 5.0-6: Upgraded to design system v2 tokens.
 * Thinking state uses pulse animation via --ease-editorial.
 */

import { ThinkingProcess, type ThinkingStep } from '@/app/components/ThinkingProcess';
import { Loader2 } from 'lucide-react';
import { clsx } from 'clsx';

interface ReasoningPanelProps {
  visible: boolean;
  steps: ThinkingStep[];
  durationSeconds: number;
  /** Whether the panel is actively thinking (streaming) */
  isThinking?: boolean;
  isZh?: boolean;
}

export function ReasoningPanel({
  visible,
  steps,
  durationSeconds,
  isThinking = false,
  isZh = true,
}: ReasoningPanelProps) {
  if (!visible || steps.length === 0) {
    return null;
  }

  return (
    <div className={clsx(
      'mt-4 rounded-lg border border-border/40 bg-muted/10 p-3 transition-all duration-[var(--duration-normal)] ease-[var(--ease-editorial)]',
      isThinking && 'border-primary/20 bg-primary/5',
    )}>
      {/* Thinking indicator */}
      {isThinking && (
        <div className="flex items-center gap-1.5 mb-2 text-xs text-primary/70">
          <Loader2 className="w-3 h-3 animate-spin" />
          <span>{isZh ? '正在思考...' : 'Thinking...'}</span>
        </div>
      )}

      <ThinkingProcess
        steps={steps}
        duration={durationSeconds}
        onComplete={() => {}}
        autoCollapse={true}
      />
    </div>
  );
}
