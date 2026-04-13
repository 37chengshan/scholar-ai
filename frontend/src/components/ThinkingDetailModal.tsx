/**
 * Thinking Detail Modal Component
 *
 * Modal showing Agent execution details:
 * - Step timeline visualization
 * - Tool call history
 * - Token usage statistics
 *
 * Part of Agent-Native Chat architecture.
 */

import { useEffect, useRef } from 'react';
import { clsx } from 'clsx';
import { StepTimeline } from './StepTimeline';
import { ToolCallCard } from './ToolCallCard';

/**
 * Step status types
 */
export type StepStatus = 'pending' | 'running' | 'success' | 'error';

/**
 * Step in execution timeline
 */
export interface Step {
  name: string;
  status: StepStatus;
  duration?: number;
  thought?: string;
}

/**
 * Tool call status types
 */
export type ToolCallStatus = 'pending' | 'running' | 'success' | 'error';

/**
 * Tool call record
 */
export interface ToolCall {
  tool: string;
  parameters: Record<string, unknown>;
  status: ToolCallStatus;
  result?: unknown;
  error?: string;
  duration?: number;
  usedFallback?: boolean;
  fallbackTool?: string;
}

/**
 * Token usage statistics
 */
export interface TokenUsage {
  used: number;
  cost: number;
}

/**
 * Modal props
 */
export interface ThinkingDetailModalProps {
  /** Modal visibility */
  isOpen: boolean;
  /** Close handler */
  onClose: () => void;
  /** Execution steps */
  steps: Step[];
  /** Tool call history */
  toolCalls: ToolCall[];
  /** Token usage stats */
  tokenUsage?: TokenUsage;
}

/**
 * ThinkingDetailModal component
 */
export function ThinkingDetailModal({
  isOpen,
  onClose,
  steps,
  toolCalls,
  tokenUsage,
}: ThinkingDetailModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);

  // Close on escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={modalRef}
        className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-lg font-semibold">思考详情</h2>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 text-xl"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="p-4 overflow-y-auto max-h-[60vh]">
          {/* Step Timeline */}
          <section className="mb-4">
            <h3 className="text-sm font-medium text-slate-600 mb-2">
              执行步骤 ({steps.length})
            </h3>
            <StepTimeline steps={steps} />
          </section>

          {/* Tool Calls */}
          {toolCalls.length > 0 && (
            <section className="mb-4">
              <h3 className="text-sm font-medium text-slate-600 mb-2">
                工具调用 ({toolCalls.length})
              </h3>
              <div className="space-y-2">
                {toolCalls.map((tc, i) => (
                  <ToolCallCard key={i} {...tc} />
                ))}
              </div>
            </section>
          )}
        </div>

        {/* Footer: Token Usage */}
        {tokenUsage && (
          <div className="p-4 border-t bg-slate-50 flex justify-between text-xs">
            <span>
              Token用量: {tokenUsage.used.toLocaleString()} tokens
            </span>
            <span>
              成本: ¥{tokenUsage.cost.toFixed(4)}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

export default ThinkingDetailModal;