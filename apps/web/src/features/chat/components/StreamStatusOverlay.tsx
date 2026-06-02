/**
 * StreamStatusOverlay - Lightweight status bar during streaming
 *
 * Displays at the bottom of the message feed during active streaming.
 * Shows contextual status messages based on the current agent phase.
 */

import { Loader2 } from 'lucide-react';
import { clsx } from 'clsx';
import type { StreamStatus } from '@/types/chat';
import type { AgentPhase } from '@/types/chat';

interface StreamStatusOverlayProps {
  streamStatus: StreamStatus;
  currentPhase: AgentPhase;
  phaseLabel?: string;
  isZh?: boolean;
}

function getPhaseMessage(phase: AgentPhase, isZh: boolean): string {
  switch (phase) {
    case 'analyzing':
      return isZh ? '正在分析问题...' : 'Analyzing question...';
    case 'retrieving':
      return isZh ? '正在检索文献...' : 'Searching papers...';
    case 'reading':
      return isZh ? '正在阅读文档...' : 'Reading documents...';
    case 'tool_calling':
      return isZh ? '正在调用工具...' : 'Calling tools...';
    case 'synthesizing':
      return isZh ? '正在生成回答...' : 'Generating answer...';
    case 'verifying':
      return isZh ? '正在验证结果...' : 'Verifying results...';
    case 'done':
      return isZh ? '完成' : 'Done';
    case 'error':
      return isZh ? '出错了' : 'Error occurred';
    default:
      return isZh ? '正在处理...' : 'Processing...';
  }
}

export function StreamStatusOverlay({
  streamStatus,
  currentPhase,
  phaseLabel,
  isZh = true,
}: StreamStatusOverlayProps) {
  // Only show during active streaming states
  if (streamStatus !== 'streaming' && streamStatus !== 'connecting' && streamStatus !== 'retrying') {
    return null;
  }

  const message = phaseLabel || getPhaseMessage(currentPhase, isZh);

  return (
    <div
      className={clsx(
        'flex items-center gap-2 px-3 py-1.5 text-[11px] text-muted-foreground',
        'bg-background/80 backdrop-blur-sm border-t border-border/30',
        'transition-opacity duration-[var(--duration-fast)]',
      )}
      role="status"
      aria-live="polite"
    >
      <Loader2 className="w-3 h-3 animate-spin text-primary/60" />
      <span>{message}</span>
      {streamStatus === 'retrying' && (
        <span className="text-amber-500 text-[10px]">
          {isZh ? '(重试中)' : '(retrying)'}
        </span>
      )}
    </div>
  );
}
