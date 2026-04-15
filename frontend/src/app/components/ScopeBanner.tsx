import { FileText, Database, AlertTriangle } from 'lucide-react';
import { cn } from './ui/utils';

export type ScopeType = 'single_paper' | 'full_kb' | 'error' | null;

interface ScopeBannerProps {
  type: ScopeType;
  title?: string;  // Paper title or KB name
  errorMessage?: string;  // For error state
}

export function ScopeBanner({ type, title, errorMessage }: ScopeBannerProps) {
  // D-04: Colors - single_paper: green, full_kb: blue, error: red
  const bgColor = {
    single_paper: 'bg-[#22c55e]',
    full_kb: 'bg-[#3b82f6]',
    error: 'bg-[#ef4444]',
  }[type || ''] || 'bg-gray-500';

  const Icon = {
    single_paper: FileText,
    full_kb: Database,
    error: AlertTriangle,
  }[type || ''] || FileText;

  // D-05: 文案
  const message = {
    single_paper: `📄 单论文模式 — ${title || '加载中...'}`,
    full_kb: `📚 全库模式 — ${title || '加载中...'}`,
    error: `⚠️ 作用域无效 — ${errorMessage || '参数无效'}`,
  }[type || ''] || null;

  if (!type || type === 'default') return null;

  return (
    <div className={cn(
      'w-full py-2 px-4 flex items-center justify-center gap-2 text-white text-sm font-medium',
      bgColor
    )}>
      <Icon className="w-4 h-4" />
      <span>{message}</span>
    </div>
  );
}

export default ScopeBanner;
