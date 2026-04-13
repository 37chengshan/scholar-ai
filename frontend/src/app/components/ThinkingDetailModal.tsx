/**
 * ThinkingDetailModal Component
 *
 * Modal for displaying detailed thinking process.
 * Shows Step Timeline, Tool Calls list, and Token Usage footer.
 *
 * Part of Agent-Native Chat (Task 3.3)
 */

import { useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { X, Activity, Coins } from 'lucide-react';
import { clsx } from 'clsx';
import { useLanguage } from '../contexts/LanguageContext';
import { StepTimeline, Step } from './StepTimeline';
import { ToolCallCard } from './ToolCallCard';
import { ToolCall } from '../../types/chat';

/**
 * Token usage data
 */
export interface TokenUsageData {
  used: number;
  cost: number;
}

/**
 * ThinkingDetailModal props
 */
export interface ThinkingDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  steps: Step[];
  toolCalls: ToolCall[];
  tokenUsage?: TokenUsageData;
}

/**
 * ThinkingDetailModal Component
 *
 * Full-screen modal with scrollable content area.
 * Supports ESC key close and click-outside close.
 */
export function ThinkingDetailModal({
  isOpen,
  onClose,
  steps,
  toolCalls,
  tokenUsage,
}: ThinkingDetailModalProps) {
  const { language } = useLanguage();
  const isZh = language === 'zh';

  // Handle ESC key close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  const t = {
    title: isZh ? '思考详情' : 'Thinking Details',
    stepTimeline: isZh ? '执行步骤' : 'Execution Steps',
    toolCalls: isZh ? '工具调用' : 'Tool Calls',
    tokenUsage: isZh ? 'Token 消耗' : 'Token Usage',
    tokens: isZh ? 'Tokens' : 'Tokens',
    cost: isZh ? '成本' : 'Cost',
    noSteps: isZh ? '暂无执行步骤' : 'No execution steps',
    noToolCalls: isZh ? '暂无工具调用' : 'No tool calls',
    close: isZh ? '关闭' : 'Close',
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop - click to close */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm"
            onClick={onClose}
          />

          {/* Modal container */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-4 z-50 flex items-center justify-center pointer-events-none"
          >
            <div
              className={clsx(
                'bg-background rounded-xl shadow-2xl border border-border/50',
                'w-full max-w-2xl max-h-[80vh]',
                'flex flex-col overflow-hidden',
                'pointer-events-auto'
              )}
            >
              {/* Header */}
              <div className="flex items-center justify-between px-5 py-4 border-b border-border/50">
                <h2 className="text-lg font-bold flex items-center gap-2">
                  <Activity className="w-5 h-5 text-primary" />
                  {t.title}
                </h2>
                <button
                  onClick={onClose}
                  className="rounded-lg p-1.5 hover:bg-muted transition-colors"
                  aria-label={t.close}
                >
                  <X className="w-5 h-5 text-muted-foreground" />
                </button>
              </div>

              {/* Content - scrollable */}
              <div className="flex-1 overflow-y-auto px-5 py-4 space-y-6">
                {/* Step Timeline section */}
                <section>
                  <h3 className="text-sm font-bold tracking-wide uppercase text-muted-foreground mb-3">
                    {t.stepTimeline}
                  </h3>
                  {steps.length > 0 ? (
                    <StepTimeline steps={steps} />
                  ) : (
                    <div className="text-center py-4 text-muted-foreground text-sm">
                      {t.noSteps}
                    </div>
                  )}
                </section>

                {/* Tool Calls section */}
                <section>
                  <h3 className="text-sm font-bold tracking-wide uppercase text-muted-foreground mb-3">
                    {t.toolCalls}
                  </h3>
                  {toolCalls.length > 0 ? (
                    <div className="space-y-2">
                      {toolCalls.map((toolCall) => (
                        <ToolCallCard key={toolCall.id} toolCall={toolCall} />
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-4 text-muted-foreground text-sm">
                      {t.noToolCalls}
                    </div>
                  )}
                </section>
              </div>

              {/* Footer - Token Usage */}
              <div className="px-5 py-3 border-t border-border/50 bg-muted/30">
                <div className="flex items-center justify-between text-sm">
                  {tokenUsage ? (
                    <>
                      <div className="flex items-center gap-4">
                        <div className="flex items-center gap-1.5">
                          <Activity className="w-4 h-4 text-muted-foreground" />
                          <span className="text-muted-foreground">{t.tokens}:</span>
                          <span className="font-mono font-medium">
                            {tokenUsage.used.toLocaleString()}
                          </span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <Coins className="w-4 h-4 text-muted-foreground" />
                          <span className="text-muted-foreground">{t.cost}:</span>
                          <span className="font-mono font-medium text-green-600">
                            ${tokenUsage.cost.toFixed(4)}
                          </span>
                        </div>
                      </div>
                    </>
                  ) : (
                    <div className="text-muted-foreground">
                      {isZh ? 'Token 统计暂不可用' : 'Token usage not available'}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

export type { ThinkingDetailModalProps as ThinkingDetailModalPropsType };