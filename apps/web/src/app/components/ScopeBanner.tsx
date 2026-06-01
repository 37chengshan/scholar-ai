import { FileText, Database, AlertTriangle, X } from 'lucide-react';
import { cn } from './ui/utils';

export type ScopeType = 'single_paper' | 'full_kb' | 'compare' | 'error' | null;

interface ScopeBannerProps {
  type: ScopeType;
  title?: string;  // Paper title or KB name
  errorMessage?: string;  // For error state
  onExitScope?: () => void;
}

export function ScopeBanner({
  type,
  title,
  errorMessage,
  onExitScope,
}: ScopeBannerProps) {
  // Return null for default/null states
  if (type === null) return null;

  // D-04: Colors - single_paper: green, full_kb: blue, error: red
  const bgColor: Record<string, string> = {
    single_paper: 'bg-[oklch(0.625_0.175_145)]',
    full_kb: 'bg-[oklch(0.625_0.145_240)]',
    compare: 'bg-[oklch(0.585_0.155_305)]',
    error: 'bg-[oklch(0.545_0.220_25)]',
  };
  const bgColorValue = bgColor[type] || 'bg-gray-500';

  // D-04: Icons
  const iconMap: Record<string, typeof FileText> = {
    single_paper: FileText,
    full_kb: Database,
    compare: Database,
    error: AlertTriangle,
  };
  const Icon = iconMap[type] || FileText;

  // D-05: 文案
  const messageMap: Record<string, string> = {
    single_paper: `📄 单论文模式 — ${title || '加载中...'}`,
    full_kb: `📚 全库模式 — ${title || '加载中...'}`,
    compare: `🧩 对比模式 — ${title || '加载中...'}`,
    error: `⚠️ 作用域无效 — ${errorMessage || '参数无效'}`,
  };
  const message = messageMap[type] || null;

  return (
    <div className={cn(
      'w-full py-2 px-4 flex items-center justify-between gap-2 text-white text-sm font-medium',
      bgColorValue
    )}>
      <div className="flex items-center gap-2">
        <Icon className="w-4 h-4" />
        <span>{message}</span>
      </div>

      {onExitScope && (
        <button
          onClick={onExitScope}
          className="inline-flex items-center gap-1 rounded border border-white/40 px-2 py-0.5 text-xs hover:bg-white/15 transition-colors"
          type="button"
        >
          <X className="w-3 h-3" />
          退出作用域
        </button>
      )}
    </div>
  );
}

export default ScopeBanner;
