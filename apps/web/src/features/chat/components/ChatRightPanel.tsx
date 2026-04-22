import { PanelRightClose } from 'lucide-react';
import { motion } from 'motion/react';
import { memo, useMemo } from 'react';
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
  onClose: () => void;
  isZh: boolean;
}

function ChatRightPanelBase({
  selectedMessage,
  streamState,
  activeRun,
  sessionTokens,
  sessionCost,
  onStop,
  onClose,
  isZh,
}: ChatRightPanelProps) {
  const timelineItems = useMemo(() => activeRun.timeline, [activeRun.timeline]);
  const evidenceItems = useMemo(() => activeRun.evidence, [activeRun.evidence]);
  const plannerMetaRows = useMemo(() => {
    const outcome = activeRun.outcome;
    return [
      { label: 'query_family', value: outcome.queryFamily },
      { label: 'planner_query_count', value: outcome.plannerQueryCount },
      { label: 'decontextualized_query', value: outcome.decontextualizedQuery },
      { label: 'second_pass_used', value: outcome.secondPassUsed },
      { label: 'second_pass_gain', value: outcome.secondPassGain },
      { label: 'evidence_bundle_hit_count', value: outcome.evidenceBundleHitCount },
    ].filter((row) => row.value !== undefined && row.value !== null && row.value !== '');
  }, [activeRun.outcome]);

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20 }}
      className="hidden min-w-[320px] shrink-0 border-l border-border/40 bg-paper-1/72 backdrop-blur-md xl:flex xl:w-[320px] xl:flex-col"
    >
      <div className="sticky top-0 z-10 border-b border-border/40 bg-background/78 px-5 py-4 backdrop-blur-md">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="font-serif text-lg font-bold tracking-tight">Agent Status</h2>
            <p className="mt-0.5 text-[8px] font-bold uppercase tracking-[0.2em] text-muted-foreground">Inspector</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl border border-border/70 bg-paper-2 text-foreground/60 transition-colors hover:text-primary"
            aria-label={isZh ? '收起右侧栏' : 'Hide panel'}
            title={isZh ? '收起右侧栏' : 'Hide panel'}
          >
            <PanelRightClose className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        <AgentStateSidebar
          className="w-full border-l-0 bg-transparent"
          selectedMessage={selectedMessage}
          currentRunningState={streamState.streamStatus === 'streaming' ? streamState : undefined}
          onStop={onStop}
        />

        {timelineItems.length > 0 ? (
          <div className="border-t border-border/50 px-5 py-4">
            <h3 className="text-[9px] font-bold tracking-[0.3em] uppercase text-muted-foreground border-b border-border/50 pb-1.5 mb-3 flex items-center gap-1.5">
              Run Timeline
            </h3>
            <ExecutionTimeline items={timelineItems} collapsed />
        </div>
      ) : null}

      {evidenceItems.length > 0 ? (
        <div className="border-t border-border/50 px-5 py-4">
          <EvidencePanel evidence={evidenceItems} maxVisible={6} />
        </div>
      ) : null}

      {plannerMetaRows.length > 0 ? (
        <div className="border-t border-border/50 px-5 py-4">
          <h3 className="text-[9px] font-bold tracking-[0.3em] uppercase text-muted-foreground border-b border-border/50 pb-1.5 mb-3">
            Planner / Evidence
          </h3>
          <dl className="space-y-2 text-xs">
            {plannerMetaRows.map((row) => (
              <div key={row.label} className="grid grid-cols-[1fr_auto] gap-2">
                <dt className="text-muted-foreground">{row.label}</dt>
                <dd className="text-foreground break-all">{String(row.value)}</dd>
              </div>
            ))}
          </dl>
        </div>
      ) : null}

      {sessionTokens > 0 && (
        <div className="border-t border-border/50 px-5 py-4">
          <TokenMonitor
            tokens={sessionTokens}
            cost={sessionCost}
            limit={128000}
          />
        </div>
      )}
      </div>
    </motion.div>
  );
}

export const ChatRightPanel = memo(ChatRightPanelBase);
