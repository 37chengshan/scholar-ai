import { useWorkflowTimeline, useWorkflowUiState } from '@/features/workflow/state/workflowSelectors';
import { workflowActions } from '@/features/workflow/state/workflowActions';
import { useLanguage } from '@/app/contexts/LanguageContext';

export function ActivityTimelineDrawer() {
  const timeline = useWorkflowTimeline();
  const ui = useWorkflowUiState();
  const { language } = useLanguage();
  const isZh = language === 'zh';

  if (!ui.showTimelineDrawer) {
    return null;
  }

  return (
    <aside className="fixed right-0 top-14 z-40 h-[calc(100vh-3.5rem)] w-[320px] border-l border-border/50 bg-background p-4 shadow-lg">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">{isZh ? '最近活动' : 'Recent Activity'}</h3>
        <button
          className="text-xs text-zinc-500500 hover:text-zinc-500800"
          onClick={() => workflowActions.setTimelineDrawer(false)}
        >
          {isZh ? '关闭' : 'Close'}
        </button>
      </div>
      <div className="mt-4 space-y-3">
        {timeline.length === 0 ? (
          <p className="text-xs text-zinc-500500">{isZh ? '还没有工作流活动。' : 'No workflow activity yet.'}</p>
        ) : (
          timeline.map((event) => (
            <div key={event.id} className="rounded border border-border/50 p-2">
              <div className="text-xs font-semibold text-zinc-500900">{event.title}</div>
              <div className="mt-1 text-xs text-zinc-500600">{event.description}</div>
              <div className="mt-1 text-[10px] text-zinc-500400">{new Date(event.at).toLocaleString()}</div>
            </div>
          ))
        )}
      </div>
    </aside>
  );
}
