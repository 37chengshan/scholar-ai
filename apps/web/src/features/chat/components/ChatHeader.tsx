import { ChevronLeft, ChevronRight, PanelRight } from 'lucide-react';

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
    <div className="h-11 px-4 border-b border-border/70 flex items-center justify-between bg-paper-1/95 flex-shrink-0">
      <h2 className="text-sm font-serif font-semibold text-foreground/85 truncate max-w-[60%]">{title}</h2>
      <button
        type="button"
        onClick={onToggleRightPanel}
        className="hidden xl:inline-flex items-center gap-1.5 px-2.5 py-1.5 text-[11px] font-medium text-muted-foreground hover:text-foreground hover:bg-muted rounded-sm transition-colors"
        aria-pressed={showRightPanel}
        aria-label={showRightPanel ? (isZh ? '收起右侧栏' : 'Hide panel') : (isZh ? '展开右侧栏' : 'Show panel')}
      >
        <PanelRight className="w-3.5 h-3.5" />
        {showRightPanel
          ? (isZh ? '收起' : 'Hide')
          : (isZh ? '展开详情' : 'Details')
        }
        {showRightPanel ? <ChevronRight className="w-3 h-3" /> : <ChevronLeft className="w-3 h-3" />}
      </button>
    </div>
  );
}

