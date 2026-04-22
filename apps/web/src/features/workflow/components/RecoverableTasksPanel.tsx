import { resolveWorkflowCopy } from '@/features/workflow/resolvers/workflowResolvers';
import { useWorkflowRecoverableTasks } from '@/features/workflow/state/workflowSelectors';
import { useLanguage } from '@/app/contexts/LanguageContext';

export function RecoverableTasksPanel() {
  const tasks = useWorkflowRecoverableTasks();
  const { language } = useLanguage();
  const isZh = language === 'zh';

  return (
    <section className="rounded-2xl border border-border/70 bg-[#fffdf9] p-4 shadow-sm">
      <h3 className="text-[10px] font-bold uppercase tracking-[0.16em] text-muted-foreground">
        {isZh ? '可恢复任务' : resolveWorkflowCopy('recoverable')}
      </h3>
      <div className="mt-3 space-y-2">
        {tasks.length === 0 ? (
          <p className="text-xs text-muted-foreground">{isZh ? '当前没有可恢复任务。' : 'No recoverable tasks.'}</p>
        ) : (
          tasks.map((task) => (
            <div key={task.id} className="rounded-xl border border-rose-200 bg-rose-50/80 px-3 py-2.5">
              <div className="text-xs font-semibold text-rose-700">{task.label}</div>
              <div className="mt-1 text-xs text-rose-600">{task.description}</div>
            </div>
          ))
        )}
      </div>
    </section>
  );
}
