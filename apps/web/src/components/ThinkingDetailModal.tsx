/**
 * Deprecated compatibility component.
 *
 * Keep the legacy API stable for older callers and tests.
 * New product work should land in `src/app/components/ThinkingDetailModal.tsx`.
 */

import { useEffect, useRef } from 'react';
import { StepTimeline } from './StepTimeline';
import { ToolCallCard } from './ToolCallCard';

export type StepStatus = 'pending' | 'running' | 'success' | 'error';

export interface Step {
  name: string;
  status: StepStatus;
  duration?: number;
  thought?: string;
}

export type ToolCallStatus = 'pending' | 'running' | 'success' | 'error';

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

export interface TokenUsage {
  used: number;
  cost: number;
}

export interface ThinkingDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  steps: Step[];
  toolCalls: ToolCall[];
  tokenUsage?: TokenUsage;
}

export function ThinkingDetailModal({
  isOpen,
  onClose,
  steps,
  toolCalls,
  tokenUsage,
}: ThinkingDetailModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);

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
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-lg font-semibold">思考详情</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-xl">
            ✕
          </button>
        </div>

        <div className="p-4 overflow-y-auto max-h-[60vh]">
          <section className="mb-4">
            <h3 className="text-sm font-medium text-slate-600 mb-2">
              执行步骤 ({steps.length})
            </h3>
            <StepTimeline steps={steps} />
          </section>

          {toolCalls.length > 0 && (
            <section className="mb-4">
              <h3 className="text-sm font-medium text-slate-600 mb-2">
                工具调用 ({toolCalls.length})
              </h3>
              <div className="space-y-2">
                {toolCalls.map((toolCall, index) => (
                  <ToolCallCard key={`${toolCall.tool}-${index}`} {...toolCall} />
                ))}
              </div>
            </section>
          )}
        </div>

        {tokenUsage && (
          <div className="p-4 border-t bg-slate-50 flex justify-between text-xs">
            <span>Token用量: {tokenUsage.used.toLocaleString()} tokens</span>
            <span>成本: ¥{tokenUsage.cost.toFixed(4)}</span>
          </div>
        )}
      </div>
    </div>
  );
}

export type { ThinkingDetailModalProps as ThinkingDetailModalPropsType };
export { ThinkingDetailModal as default };
