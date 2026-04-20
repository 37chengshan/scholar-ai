import { mapScopeToBannerModel } from '@/features/workflow/adapters/workflowAdapters';
import { useWorkflowScope } from '@/features/workflow/state/workflowSelectors';

export function ActiveScopeBanner() {
  const scope = useWorkflowScope();
  const banner = mapScopeToBannerModel(scope);

  return (
    <div className="rounded-md border border-zinc-200 bg-zinc-50 px-4 py-3">
      <div className="text-[10px] font-bold uppercase tracking-[0.18em] text-zinc-500">Current Scope</div>
      <div className="mt-1 text-sm font-semibold text-zinc-900">{banner.title}</div>
      <div className="mt-1 text-xs text-zinc-600">{banner.subtitle}</div>
    </div>
  );
}
