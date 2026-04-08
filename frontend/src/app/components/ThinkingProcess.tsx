/**
 * ThinkingProcess Component
 *
 * Collapsible thinking process display with auto-collapse after 1-2 seconds.
 * Shows the complete Planner→Executor→Verifier chain.
 *
 * Part of Agent-Native architecture (D-19, D-20, D-21)
 */

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { ChevronUp, ChevronDown, Brain } from 'lucide-react';
import { clsx } from 'clsx';
import { useLanguage } from '../contexts/LanguageContext';

/**
 * Thinking step type
 */
export type ThinkingStepType = 'analyze' | 'plan' | 'execute' | 'verify';

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
}

/**
 * Get label for step type
 */
function getStepLabel(type: ThinkingStepType, isZh: boolean): string {
  const labels: Record<ThinkingStepType, { en: string; zh: string }> = {
    analyze: { en: 'Analyzing', zh: '分析中' },
    plan: { en: 'Planning', zh: '规划中' },
    execute: { en: 'Executing', zh: '执行中' },
    verify: { en: 'Verifying', zh: '验证中' },
  };
  return isZh ? labels[type].zh : labels[type].en;
}

/**
 * Get icon color for step type
 */
function getStepColor(type: ThinkingStepType): string {
  const colors: Record<ThinkingStepType, string> = {
    analyze: 'text-blue-500',
    plan: 'text-purple-500',
    execute: 'text-primary',
    verify: 'text-green-500',
  };
  return colors[type];
}

/**
 * Get background color for step type
 */
function getStepBgColor(type: ThinkingStepType): string {
  const colors: Record<ThinkingStepType, string> = {
    analyze: 'bg-blue-50',
    plan: 'bg-purple-50',
    execute: 'bg-primary/10',
    verify: 'bg-green-50',
  };
  return colors[type];
}

/**
 * ThinkingProcess Component
 *
 * Displays thinking steps with auto-collapse functionality.
 * Auto-collapses after 1.5 seconds (per D-20: 1-2 seconds).
 */
export function ThinkingProcess({ 
  steps, 
  duration, 
  onComplete,
  className 
}: ThinkingProcessProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const { language } = useLanguage();
  const isZh = language === 'zh';

  // Auto-collapse after 1.5 seconds (per D-20)
  useEffect(() => {
    if (steps.length === 0) return;

    const timer = setTimeout(() => {
      setIsExpanded(false);
      onComplete?.();
    }, 1500);

    return () => clearTimeout(timer);
  }, [steps.length, onComplete]);

  const t = {
    thoughtProcess: isZh ? '思考过程' : 'Thought process',
    seconds: isZh ? '秒' : 's',
    analyzing: isZh ? '分析中' : 'Analyzing',
    planning: isZh ? '规划中' : 'Planning',
    verifying: isZh ? '验证中' : 'Verifying',
  };

  return (
    <div
      className={clsx(
        'border border-primary/30 rounded-lg overflow-hidden bg-primary/5',
        className
      )}
    >
      {/* Header (always visible) */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-3 py-2 bg-primary/5 hover:bg-primary/10 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Brain className="w-4 h-4 text-primary" />
          <span className="text-sm font-medium text-primary">
            {t.thoughtProcess} ({duration.toFixed(1)}{t.seconds})
          </span>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4 text-primary" />
        ) : (
          <ChevronDown className="w-4 h-4 text-primary" />
        )}
      </button>

      {/* Expandable content */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="overflow-hidden"
          >
            <div className="p-3 space-y-2">
              {steps.map((step, idx) => (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: idx * 0.1 }}
                  className={clsx(
                    'flex items-start gap-2 p-2 rounded-sm',
                    getStepBgColor(step.type)
                  )}
                >
                  <div className={clsx('flex-shrink-0 mt-0.5', getStepColor(step.type))}>
                    <Brain className="w-3.5 h-3.5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className={clsx('text-xs font-medium mb-0.5', getStepColor(step.type))}>
                      {getStepLabel(step.type, isZh)}
                    </div>
                    <div className="text-xs text-muted-foreground whitespace-pre-wrap">
                      {step.content}
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export type { ThinkingProcessProps as ThinkingProcessPropsType };