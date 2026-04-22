import { mapScopeToBannerModel } from '@/features/workflow/adapters/workflowAdapters';
import { useWorkflowScope } from '@/features/workflow/state/workflowSelectors';
import { useLanguage } from '@/app/contexts/LanguageContext';

export function ActiveScopeBanner() {
  const scope = useWorkflowScope();
  const banner = mapScopeToBannerModel(scope);
  const { language } = useLanguage();
  const isZh = language === 'zh';

  return (
    <div className="rounded-2xl border border-border/70 bg-[#fffdf9] px-4 py-3 shadow-sm">
      <div className="text-[10px] font-bold uppercase tracking-[0.18em] text-muted-foreground">
        {isZh ? '当前范围' : 'Current Scope'}
      </div>
      <div className="mt-1 text-sm font-semibold text-foreground">{banner.title}</div>
      <div className="mt-1 text-xs leading-relaxed text-muted-foreground">{banner.subtitle}</div>
    </div>
  );
}
