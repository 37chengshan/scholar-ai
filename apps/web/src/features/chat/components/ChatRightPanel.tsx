import { motion } from 'motion/react';
import { AgentStateSidebar } from '@/app/components/AgentStateSidebar';
import { TokenMonitor } from '@/app/components/TokenMonitor';
import { EvidencePanel } from '@/features/chat/components/workbench/EvidencePanel';
import { ExecutionTimeline } from '@/features/chat/components/workbench/ExecutionTimeline';
import type { ChatMessage as RichChatMessage } from '@/app/components/ChatMessageCard';
import type { ChatStreamState } from '@/app/hooks/useChatStream';
import type { AgentRun } from '@/features/chat/types/run';

interface ChatRightPanelProps {
  selectedMessage?: RichChatMessage;
  streamState: ChatStreamState;
  activeRun: AgentRun;
  sessionTokens: number;
  sessionCost: number;
  onStop: () => void;
}

export function ChatRightPanel({
  selectedMessage,
  streamState,
  activeRun,
  sessionTokens,
  sessionCost,
  onStop,
}: ChatRightPanelProps) {
  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20 }}
      className="w-[300px] border-l border-zinc-200 flex-shrink-0 hidden xl:block bg-zinc-50/60"
    >
      <AgentStateSidebar
        selectedMessage={selectedMessage}
        currentRunningState={streamState.streamStatus === 'streaming' ? streamState : undefined}
        onStop={onStop}
      />

      {activeRun.timeline.length > 0 ? (
        <div className="border-t border-border/50 p-4">
          <div className="mb-2 text-[10px] font-bold uppercase tracking-[0.16em] text-zinc-500">
            Run Timeline
          </div>
          <ExecutionTimeline items={activeRun.timeline} collapsed />
        </div>
      ) : null}

      {activeRun.evidence.length > 0 ? (
        <div className="border-t border-border/50 p-4">
          <EvidencePanel evidence={activeRun.evidence} maxVisible={6} />
        </div>
      ) : null}

      {sessionTokens > 0 && (
        <div className="border-t border-border/50 p-4">
          <TokenMonitor
            tokens={sessionTokens}
            cost={sessionCost}
            limit={128000}
          />
        </div>
      )}
    </motion.div>
  );
}
