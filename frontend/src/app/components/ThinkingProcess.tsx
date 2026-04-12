/**
 * ThinkingProcess Component
 *
 * Inline thinking process display with auto-collapse after 1.5s (D-02, D-03).
 * Shows the complete Planner→Executor→Verifier chain with step-specific icons.
 *豆包/DeepSeek style: purple left border, subtle purple background.
 *
 * Part of Agent-Native architecture (D-19, D-20, D-21)
 */

import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Brain, ListChecks, Play, CheckCircle } from 'lucide-react';
import { clsx } from 'clsx';
import { useLanguage } from '../contexts/LanguageContext';

/**
 * Thinking step type
 * Includes 'thinking' from backend AgentRunner (default thought type)
 */
export type ThinkingStepType = 'thinking' | 'analyze' | 'plan' | 'execute' | 'verify';

/**
 * Single thinking step
 */
export interface ThinkingStep {
  type: ThinkingStepType;
  content: string;
  timestamp?: number;
}

/**
 * ThinkingProcess props
 */
export interface ThinkingProcessProps {
  steps: ThinkingStep[];
  duration: number; // seconds
  onComplete?: () => void;
  className?: string;
  /** Whether to auto-collapse after thinking completes. Default: true */
  autoCollapse?: boolean;
}

/**
 * Get icon component for step type
 * 'thinking' uses Brain icon (default from backend AgentRunner)
 */
function getStepIcon(type: ThinkingStepType) {
  const icons: Record<ThinkingStepType, React.ElementType> = {
    thinking: Brain,
    analyze: Brain,
    plan: ListChecks,
    execute: Play,
    verify: CheckCircle,
  };
  return icons[type];
}

/**
 * Get icon color for step type
 * 'thinking' uses purple (matches component's purple theme)
 */
function getStepColor(type: ThinkingStepType): string {
  const colors: Record<ThinkingStepType, string> = {
    thinking: 'text-purple-500',
    analyze: 'text-blue-500',
    plan: 'text-purple-500',
    execute: 'text-[#d35400]',
    verify: 'text-green-500',
  };
  return colors[type];
}

/**
 * Format relative time from timestamp
 */
function formatRelativeTime(timestamp: number | undefined, isZh: boolean): string {
  if (!timestamp) return '';
  const now = Date.now();
  const diff = now - timestamp;
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return isZh ? `${seconds}秒前` : `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return isZh ? `${minutes}分钟前` : `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  return isZh ? `${hours}小时前` : `${hours}h ago`;
}

/**
 * ThinkingProcess Component
 *
 * Displays thinking steps inline with purple left border (D-02).
 * Auto-collapses after 1.5s of inactivity (D-03).
 */
export function ThinkingProcess({
  steps,
  duration,
  onComplete,
  className,
  autoCollapse = true,
}: ThinkingProcessProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const { language } = useLanguage();
  const isZh = language === 'zh';
  const lastStepTime = useRef<number>(Date.now());
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Track when last step was added and start auto-collapse timer
  useEffect(() => {
    if (steps.length === 0) return;

    lastStepTime.current = Date.now();

    if (!autoCollapse) return;

    // Clear existing timer
    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }

    // Start 1.5s auto-collapse timer
    timerRef.current = setTimeout(() => {
      setIsCollapsed(true);
      onComplete?.();
    }, 1500);

    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
    };
  }, [steps.length, onComplete, autoCollapse]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
    };
  }, []);

  const t = {
    collapsedHeader: isZh ? `💭 思考过程 (${steps.length}步)` : `💭 Thought process (${steps.length} steps)`,
  };

  return (
    <div
      className={clsx(
        'border-l-2 border-[#8b5cf6]/30 pl-4 py-2 my-2 bg-purple-50/50 rounded-r-lg',
        className
      )}
    >
      {/* Collapsed header (clickable to expand) */}
      <AnimatePresence mode="wait">
        {isCollapsed ? (
          <motion.div
            key="collapsed"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <button
              onClick={() => setIsCollapsed(false)}
              className="flex items-center gap-2 text-sm text-muted-foreground cursor-pointer hover:text-foreground py-1 transition-colors"
            >
              {t.collapsedHeader}
            </button>
          </motion.div>
        ) : (
          <motion.div
            key="expanded"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            {/* Step list */}
            <div className="space-y-1.5">
              {steps.map((step, idx) => {
                const Icon = getStepIcon(step.type);
                return (
                  <motion.div
                    key={idx}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.05, duration: 0.15 }}
                    className="flex items-start gap-2"
                  >
                    <div className={clsx('flex-shrink-0 mt-0.5', getStepColor(step.type))}>
                      <Icon className="w-4 h-4" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-xs text-foreground whitespace-pre-wrap">
                        {step.content}
                      </div>
                      {step.timestamp && (
                        <div className="text-xs text-muted-foreground/60 mt-0.5">
                          {formatRelativeTime(step.timestamp, isZh)}
                        </div>
                      )}
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export type { ThinkingProcessProps as ThinkingProcessPropsType };