import { Bot, ChevronLeft, ChevronRight } from 'lucide-react';

interface ChatHeaderProps {
  title: string;
  showRightPanel: boolean;
  isZh: boolean;
  onToggleRightPanel: () => void;
}

export function ChatHeader({
  title,
  showRightPanel,
  isZh,
  onToggleRightPanel,
}: ChatHeaderProps) {
  return (
    <div className="px-6 py-3 border-b border-zinc-200 flex items-center justify-between bg-background gap-3">
      <div className="flex items-center gap-3">
        <Bot className="w-4 h-4 text-primary" />
        <h2 className="font-serif text-[15px] font-bold truncate tracking-tight">{title}</h2>
      </div>
      <button
        type="button"
        onClick={onToggleRightPanel}
        className="hidden xl:inline-flex items-center gap-2 px-3 py-1.5 border border-zinc-200 text-xs font-medium text-zinc-600 hover:text-zinc-900 hover:border-primary transition-colors"
        aria-pressed={showRightPanel}
        aria-label={showRightPanel ? (isZh ? '收起右侧栏' : 'Hide right panel') : (isZh ? '展开右侧栏' : 'Show right panel')}
      >
        {showRightPanel ? <ChevronRight className="w-3.5 h-3.5" /> : <ChevronLeft className="w-3.5 h-3.5" />}
        {showRightPanel ? (isZh ? '收起右侧栏' : 'Hide panel') : (isZh ? '展开右侧栏' : 'Open panel')}
      </button>
    </div>
  );
}
