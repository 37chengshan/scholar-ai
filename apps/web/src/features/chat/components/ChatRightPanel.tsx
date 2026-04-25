import { PanelRightClose } from 'lucide-react';
import { motion } from 'motion/react';
import { memo, useMemo } from 'react';
import { TokenMonitor } from '@/app/components/TokenMonitor';
import { EvidencePanel } from '@/features/chat/components/workbench/EvidencePanel';
import { ExecutionTimeline } from '@/features/chat/components/workbench/ExecutionTimeline';
import type { ChatMessage as RichChatMessage } from '@/app/components/ChatMessageCard';
import type { ChatStreamState } from '@/app/hooks/useChatStream';
import type { AgentRun, RunStatus } from '@/features/chat/types/run';

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

type SummaryRow = {
  label: string;
  value: string;
};

const STATUS_LABEL: Record<RunStatus, { zh: string; en: string }> = {
  idle: { zh: '空闲', en: 'Idle' },
  running: { zh: '运行中', en: 'Running' },
  waiting_confirmation: { zh: '等待确认', en: 'Waiting confirmation' },
  completed: { zh: '已完成', en: 'Completed' },
  failed: { zh: '失败', en: 'Failed' },
  cancelled: { zh: '已取消', en: 'Cancelled' },
};

function mapSummaryRows(activeRun: AgentRun, isZh: boolean): SummaryRow[] {
  const rows: SummaryRow[] = [];
  rows.push({
    label: isZh ? '状态' : 'Status',
    value: STATUS_LABEL[activeRun.status][isZh ? 'zh' : 'en'],
  });
  rows.push({ label: isZh ? '阶段' : 'Phase', value: activeRun.currentPhase || activeRun.phase });

  if (activeRun.outcome.queryFamily) {
    rows.push({ label: isZh ? '问题类型' : 'Query type', value: activeRun.outcome.queryFamily });
  }

  if (activeRun.outcome.evidenceBundleHitCount !== undefined) {
    rows.push({
      label: isZh ? '命中证据数' : 'Evidence hits',
      value: String(activeRun.outcome.evidenceBundleHitCount),
    });
  }

  if (activeRun.outcome.secondPassUsed !== undefined) {
    rows.push({
      label: isZh ? '二次检索' : 'Second pass',
      value: activeRun.outcome.secondPassUsed ? (isZh ? '是' : 'Yes') : (isZh ? '否' : 'No'),
    });
  }

  return rows;
}

function mapTechnicalRows(activeRun: AgentRun, isZh: boolean): SummaryRow[] {
  const outcome = activeRun.outcome;
  const rows: Array<SummaryRow | null> = [
    outcome.queryFamily ? { label: isZh ? 'query_family' : 'query_family', value: outcome.queryFamily } : null,
    outcome.plannerQueryCount !== undefined ? { label: isZh ? 'planner_query_count' : 'planner_query_count', value: String(outcome.plannerQueryCount) } : null,
    outcome.decontextualizedQuery ? { label: isZh ? 'decontextualized_query' : 'decontextualized_query', value: outcome.decontextualizedQuery } : null,
    outcome.secondPassUsed !== undefined ? { label: isZh ? 'second_pass_used' : 'second_pass_used', value: String(outcome.secondPassUsed) } : null,
    outcome.secondPassGain !== undefined ? { label: isZh ? 'second_pass_gain' : 'second_pass_gain', value: String(outcome.secondPassGain) } : null,
    outcome.evidenceBundleHitCount !== undefined ? { label: isZh ? 'evidence_bundle_hit_count' : 'evidence_bundle_hit_count', value: String(outcome.evidenceBundleHitCount) } : null,
    activeRun.runId ? { label: isZh ? 'run_id' : 'run_id', value: activeRun.runId } : null,
    activeRun.messageId ? { label: isZh ? 'message_id' : 'message_id', value: activeRun.messageId } : null,
  ];

  return rows.filter((row): row is SummaryRow => Boolean(row));
}

function MessageDetailCard({ selectedMessage, isZh }: { selectedMessage: RichChatMessage; isZh: boolean }) {
  return (
    <div className="rounded-md border border-border/60 bg-muted/20 px-3 py-3">
      <div className="text-[11px] font-semibold text-foreground/85">
        {isZh ? '消息详情' : 'Message detail'}
      </div>
      <div className="mt-1 text-xs text-muted-foreground">
        {isZh ? '你正在查看一条历史消息。右侧默认运行状态仍以当前 Run 为准。' : 'You are viewing a historical message. Default run status still follows active run.'}
      </div>
      <div className="mt-2 text-xs text-foreground/85 line-clamp-4 whitespace-pre-wrap">
        {selectedMessage.content || (isZh ? '该消息没有正文内容。' : 'No message content.')}
      </div>
    </div>
  );
}

function VerificationCard({ activeRun, isZh }: { activeRun: AgentRun; isZh: boolean }) {
  const consistency = activeRun.outcome.finalSummary?.answerEvidenceConsistency;
  const reasons = activeRun.outcome.finalSummary?.lowConfidenceReasons || [];

  if (consistency === undefined && reasons.length === 0) {
    return null;
  }

  const statusText = consistency === undefined
    ? (isZh ? '待验证' : 'Pending')
    : consistency >= 0.8
      ? (isZh ? '通过' : 'Pass')
      : consistency >= 0.5
        ? (isZh ? '警告' : 'Warning')
        : (isZh ? '失败' : 'Fail');

  return (
    <div className="border-t border-border/50 px-5 py-4">
      <h3 className="text-xs font-semibold text-foreground/85">{isZh ? '验证结果' : 'Verification'}</h3>
      <div className="mt-2 space-y-1 text-xs">
        <div className="flex items-center justify-between">
          <span className="text-muted-foreground">{isZh ? '状态' : 'Status'}</span>
          <span className="text-foreground">{statusText}</span>
        </div>
        {consistency !== undefined && (
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">{isZh ? '证据一致性' : 'Evidence consistency'}</span>
            <span className="text-foreground">{(consistency * 100).toFixed(0)}%</span>
          </div>
        )}
      </div>
      {reasons.length > 0 && (
        <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-muted-foreground">
          {reasons.slice(0, 3).map((reason, idx) => (
            <li key={`${reason}-${idx}`}>{reason}</li>
          ))}
        </ul>
      )}
    </div>
  );
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
  const summaryRows = useMemo(() => mapSummaryRows(activeRun, isZh), [activeRun, isZh]);
  const technicalRows = useMemo(() => mapTechnicalRows(activeRun, isZh), [activeRun, isZh]);

  const showRunMeta = activeRun.status !== 'idle' || streamState.streamStatus === 'streaming';

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
            <h2 className="text-sm font-semibold tracking-tight">{isZh ? '研究过程' : 'Research Trace'}</h2>
            <p className="mt-0.5 text-[11px] text-muted-foreground">{isZh ? '证据与推理' : 'Evidence and reasoning'}</p>
          </div>
          {streamState.streamStatus === 'streaming' ? (
            <button
              type="button"
              onClick={onStop}
              className="inline-flex h-8 items-center justify-center rounded-md border border-border/70 bg-paper-2 px-2 text-xs text-foreground/75 transition-colors hover:text-primary"
            >
              {isZh ? '停止' : 'Stop'}
            </button>
          ) : null}
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
        {selectedMessage ? (
          <div className="px-5 py-4 border-b border-border/50">
            <MessageDetailCard selectedMessage={selectedMessage} isZh={isZh} />
          </div>
        ) : null}

        {showRunMeta ? (
          <div className="border-b border-border/50 px-5 py-4">
            <h3 className="text-xs font-semibold text-foreground/85">{isZh ? '运行摘要' : 'Run Summary'}</h3>
            <dl className="mt-2 space-y-1.5 text-xs">
              {summaryRows.map((row) => (
                <div key={row.label} className="grid grid-cols-[1fr_auto] gap-2">
                  <dt className="text-muted-foreground">{row.label}</dt>
                  <dd className="text-foreground break-all text-right">{row.value}</dd>
                </div>
              ))}
            </dl>
          </div>
        ) : null}

        {evidenceItems.length > 0 ? (
          <div className="border-b border-border/50 px-5 py-4">
            <EvidencePanel evidence={evidenceItems} maxVisible={8} />
          </div>
        ) : null}

        <VerificationCard activeRun={activeRun} isZh={isZh} />

        {timelineItems.length > 0 ? (
          <div className="border-t border-border/50 px-5 py-4">
            <h3 className="mb-3 text-xs font-semibold text-foreground/85">{isZh ? '过程时间线' : 'Process'}</h3>
            <ExecutionTimeline items={timelineItems} collapsed />
          </div>
        ) : null}

        {technicalRows.length > 0 || sessionTokens > 0 ? (
          <details className="border-t border-border/50 px-5 py-4">
            <summary className="cursor-pointer text-xs font-semibold text-muted-foreground">
              {isZh ? '技术详情' : 'Technical Details'}
            </summary>
            <dl className="mt-3 space-y-1.5 text-xs">
              {technicalRows.map((row) => (
                <div key={row.label} className="grid grid-cols-[1fr_auto] gap-2">
                  <dt className="text-muted-foreground">{row.label}</dt>
                  <dd className="text-foreground break-all text-right">{row.value}</dd>
                </div>
              ))}
            </dl>
            {sessionTokens > 0 ? (
              <div className="mt-3">
                <TokenMonitor
                  tokens={sessionTokens}
                  cost={sessionCost}
                  limit={128000}
                />
              </div>
            ) : null}
          </details>
        ) : null}
      </div>
    </motion.div>
  );
}

export const ChatRightPanel = memo(ChatRightPanelBase);
