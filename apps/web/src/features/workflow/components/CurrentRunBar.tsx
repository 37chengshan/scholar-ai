import { resolveStatusBadge } from '@/features/workflow/resolvers/workflowResolvers';
import { useWorkflowCurrentRun } from '@/features/workflow/state/workflowSelectors';
import { useLanguage } from '@/app/contexts/LanguageContext';

const badgeClassByTone = {
  default: 'bg-sky-100 text-sky-700 border-sky-200',
  success: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  warning: 'bg-amber-100 text-amber-700 border-amber-200',
  danger: 'bg-rose-100 text-rose-700 border-rose-200',
  muted: 'bg-stone-100 text-stone-600 border-stone-200',
} as const;

export function CurrentRunBar() {
  const run = useWorkflowCurrentRun();
  const { language } = useLanguage();
  const isZh = language === 'zh';

  if (!run) {
    return (
      <div className="rounded-2xl border border-dashed border-border/80 bg-[#fffdf9] px-4 py-3 text-xs text-muted-foreground">
        {isZh ? '当前没有活动运行。可从对话、检索导入或资源库操作开始。' : 'No active run. Start from Chat, Search import, or Library actions.'}
      </div>
    );
  }

  const badge = resolveStatusBadge(run.status);

  return (
    <div className="rounded-2xl border border-border/70 bg-[#fffdf9] px-4 py-3 shadow-sm">
      <div className="flex flex-wrap items-center gap-2">
        <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-bold tracking-[0.12em] ${badgeClassByTone[badge.tone]}`}>
          {badge.label}
        </span>
        <span className="text-xs font-semibold text-foreground">{isZh ? `运行 #${run.id}` : `Run #${run.id}`}</span>
        <span className="text-xs text-muted-foreground">{run.stage}</span>
      </div>
      {run.nextAction ? <div className="mt-2 text-xs text-muted-foreground">{isZh ? `下一步：${run.nextAction}` : `Next: ${run.nextAction}`}</div> : null}
      {run.error ? <div className="mt-2 text-xs text-rose-600">{isZh ? `错误：${run.error}` : `Error: ${run.error}`}</div> : null}
    </div>
  );
}
