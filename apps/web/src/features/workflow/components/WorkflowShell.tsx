import { ActiveScopeBanner } from '@/features/workflow/components/ActiveScopeBanner';
import { CurrentRunBar } from '@/features/workflow/components/CurrentRunBar';
import { PendingActionsPanel } from '@/features/workflow/components/PendingActionsPanel';
import { RecoverableTasksPanel } from '@/features/workflow/components/RecoverableTasksPanel';
import { ActivityTimelineDrawer } from '@/features/workflow/components/ActivityTimelineDrawer';
import { ArtifactsDrawer } from '@/features/workflow/components/ArtifactsDrawer';
import { workflowActions } from '@/features/workflow/state/workflowActions';
import { useWorkflowHydration } from '@/features/workflow/hooks/useWorkflowHydration';
import {
  useWorkflowCurrentRun,
  useWorkflowPendingActions,
  useWorkflowRecoverableTasks,
  useWorkflowScope,
  useWorkflowUiState,
} from '@/features/workflow/state/workflowSelectors';
import { useLanguage } from '@/app/contexts/LanguageContext';
import { ChevronDown, ChevronUp, PanelsTopLeft, Sparkles } from 'lucide-react';

export function WorkflowShell() {
  useWorkflowHydration();
  const { language } = useLanguage();
  const isZh = language === 'zh';
  const scope = useWorkflowScope();
  const run = useWorkflowCurrentRun();
  const pendingActions = useWorkflowPendingActions();
  const recoverableTasks = useWorkflowRecoverableTasks();
  const ui = useWorkflowUiState();
  const hasWorkflowDetails = Boolean(run) || pendingActions.length > 0 || recoverableTasks.length > 0;

  const statusLabel = run
    ? `${run.status.toUpperCase()} · ${run.stage}`
    : isZh ? '空闲' : 'Idle';

  return (
    <>
      <section className="border-b border-border/60 bg-[#f8f2e8]/82 px-4 py-3 backdrop-blur-md lg:px-6">
        <div className="flex w-full flex-col gap-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-2xl border border-border/70 bg-[#fffdf9] shadow-sm">
                <PanelsTopLeft className="h-4 w-4 text-primary" />
              </div>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground">
                    {isZh ? '研究状态' : 'Workflow Desk'}
                  </h2>
                  <span className="inline-flex items-center rounded-full border border-border/70 bg-[#fffdf9] px-2 py-0.5 text-[10px] font-semibold text-foreground/75">
                    {statusLabel}
                  </span>
                </div>
                <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                  <span className="truncate font-medium text-foreground">{scope.title}</span>
                  <span>{isZh ? `${pendingActions.length} 个待处理` : `${pendingActions.length} pending`}</span>
                  <span>{isZh ? `${recoverableTasks.length} 个可恢复` : `${recoverableTasks.length} recoverable`}</span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => workflowActions.setArtifactsDrawer(true)}
                className="rounded-full border border-border/70 bg-[#fffdf9] px-3 py-1.5 text-[10px] font-bold uppercase tracking-[0.1em] text-foreground/75 transition-colors hover:bg-background"
              >
                {isZh ? '产物' : 'Artifacts'}
              </button>
              <button
                onClick={() => workflowActions.setTimelineDrawer(true)}
                className="rounded-full border border-border/70 bg-[#fffdf9] px-3 py-1.5 text-[10px] font-bold uppercase tracking-[0.1em] text-foreground/75 transition-colors hover:bg-background"
              >
                {isZh ? '活动' : 'Activity'}
              </button>
              <button
                onClick={() => workflowActions.setWorkflowConsole(!ui.showConsole)}
                className="inline-flex items-center gap-2 rounded-full bg-primary px-3 py-1.5 text-[10px] font-bold uppercase tracking-[0.1em] text-primary-foreground shadow-sm transition-colors hover:bg-primary/90"
                aria-expanded={ui.showConsole}
              >
                {ui.showConsole ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                {ui.showConsole ? (isZh ? '收起细节' : 'Collapse') : (isZh ? '查看细节' : 'Show Details')}
              </button>
            </div>
          </div>

          {ui.showConsole ? (
            <div className="grid gap-3 animate-in fade-in-0 slide-in-from-top-1 duration-200">
              <div className="grid gap-3 lg:grid-cols-[1.1fr_0.9fr]">
                <ActiveScopeBanner />
                <CurrentRunBar />
              </div>

              <div className="grid gap-3 lg:grid-cols-2">
                <PendingActionsPanel />
                <RecoverableTasksPanel />
              </div>
            </div>
          ) : (
            <div className="flex flex-wrap items-center gap-2 rounded-2xl border border-dashed border-border/80 bg-[#fffdf9]/80 px-4 py-2.5 text-xs text-muted-foreground">
              <Sparkles className="h-3.5 w-3.5 text-primary" />
              <span>
                {hasWorkflowDetails
                  ? isZh
                    ? '研究细节已折叠，聊天内容与输入区保持在首屏。'
                    : 'Research details are tucked away so the conversation stays front and center.'
                  : isZh
                    ? '当前没有进行中的研究任务；需要时再展开上下文细节。'
                    : 'No active research task is in focus right now; open details only when you need them.'}
              </span>
            </div>
          )}
        </div>
      </section>

      <ArtifactsDrawer />
      <ActivityTimelineDrawer />
    </>
  );
}
