import { FileText, Database, AlertTriangle } from 'lucide-react';
import { cn } from './ui/utils';

export type ScopeType = 'single_paper' | 'full_kb' | 'error' | null;

interface ScopeBannerProps {
  type: ScopeType;
  title?: string;  // Paper title or KB name
  errorMessage?: string;  // For error state
}

export function ScopeBanner({ type, title, errorMessage }: ScopeBannerProps) {
  // Return null for default/null states
  if (type === null) return null;

  // D-04: Colors - single_paper: green, full_kb: blue, error: red
  const bgColor: Record<string, string> = {
    single_paper: 'bg-[#22c55e]',
    full_kb: 'bg-[#3b82f6]',
    error: 'bg-[#ef4444]',
  };
  const bgColorValue = bgColor[type] || 'bg-gray-500';

  // D-04: Icons
  const iconMap: Record<string, typeof FileText> = {
    single_paper: FileText,
    full_kb: Database,
    error: AlertTriangle,
  };
  const Icon = iconMap[type] || FileText;

  // D-05: 文案
  const messageMap: Record<string, string> = {
    single_paper: `📄 单论文模式 — ${title || '加载中...'}`,
    full_kb: `📚 全库模式 — ${title || '加载中...'}`,
    error: `⚠️ 作用域无效 — ${errorMessage || '参数无效'}`,
  };
  const message = messageMap[type] || null;

  return (
    <div className={cn(
      'w-full py-2 px-4 flex items-center justify-center gap-2 text-white text-sm font-medium',
      bgColorValue
    )}>
      <Icon className="w-4 h-4" />
      <span>{message}</span>
    </div>
  );
}

export default ScopeBanner;
