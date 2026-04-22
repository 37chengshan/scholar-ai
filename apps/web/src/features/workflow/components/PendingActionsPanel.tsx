import { resolveWorkflowCopy } from '@/features/workflow/resolvers/workflowResolvers';
import { useWorkflowPendingActions } from '@/features/workflow/state/workflowSelectors';
import { useLanguage } from '@/app/contexts/LanguageContext';

export function PendingActionsPanel() {
  const actions = useWorkflowPendingActions();
  const { language } = useLanguage();
  const isZh = language === 'zh';

  return (
    <section className="rounded-2xl border border-border/70 bg-[#fffdf9] p-4 shadow-sm">
      <h3 className="text-[10px] font-bold uppercase tracking-[0.16em] text-muted-foreground">
        {isZh ? '待处理动作' : resolveWorkflowCopy('pending')}
      </h3>
      <div className="mt-3 space-y-2">
        {actions.length === 0 ? (
          <p className="text-xs text-muted-foreground">{isZh ? '当前范围内没有待处理动作。' : 'No pending actions in current scope.'}</p>
        ) : (
          actions.map((action) => (
            <div key={action.id} className="rounded-xl border border-border/80 bg-background/70 px-3 py-2.5">
              <div className="text-xs font-semibold text-foreground">{action.label}</div>
              <div className="mt-1 text-xs text-muted-foreground">{action.description}</div>
            </div>
          ))
        )}
      </div>
    </section>
  );
}
