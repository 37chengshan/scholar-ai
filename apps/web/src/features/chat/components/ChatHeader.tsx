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
    <div className="flex items-center justify-between gap-4 border-b border-border/70 bg-paper-1/90 px-4 py-4 backdrop-blur-sm lg:px-6">
      <div className="min-w-0">
        <div className="text-[10px] font-bold uppercase tracking-[0.24em] text-muted-foreground">
          {isZh ? "研究对话" : "Research Dialogue"}
        </div>
        <h2 className="mt-2 truncate font-serif text-xl leading-none text-foreground lg:text-2xl">
          {title}
        </h2>
      </div>

      <button
        type="button"
        onClick={onToggleRightPanel}
        className="hidden xl:inline-flex items-center gap-2 rounded-full border border-border/70 bg-paper-2 px-3 py-2 text-[11px] font-bold uppercase tracking-[0.14em] text-muted-foreground transition-colors hover:border-primary/20 hover:text-primary"
        aria-pressed={showRightPanel}
        aria-label={showRightPanel ? (isZh ? "收起右侧栏" : "Hide panel") : (isZh ? "展开右侧栏" : "Show panel")}
      >
        <PanelRight className="w-3.5 h-3.5" />
        {showRightPanel ? (isZh ? "收起上下文" : "Hide Context") : (isZh ? "展开上下文" : "Show Context")}
        {showRightPanel ? <ChevronRight className="w-3 h-3" /> : <ChevronLeft className="w-3 h-3" />}
      </button>
    </div>
  );
}
