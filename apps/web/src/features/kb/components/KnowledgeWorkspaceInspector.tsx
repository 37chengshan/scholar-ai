import { PanelRightClose, Sparkles } from 'lucide-react';

import { Button } from '@/app/components/ui/button';
import { ScrollArea } from '@/app/components/ui/scroll-area';

interface ReadinessItem {
  id: string;
  title: string;
  priority: 'blocked' | 'active' | 'ready' | string;
  statusLabel: string;
  reason: string;
  targetHref: string;
}

interface KnowledgeWorkspaceInspectorProps {
  readinessItems: ReadinessItem[];
  onRefresh: () => void | Promise<void>;
  onClose: () => void;
  onNavigate: (href: string) => void;
}

export function KnowledgeWorkspaceInspector({
  readinessItems,
  onRefresh,
  onClose,
  onNavigate,
}: KnowledgeWorkspaceInspectorProps) {
  return (
    <div className="flex h-full min-h-0 flex-col bg-stone-50/75">
      <div className="border-b border-border/50 px-5 py-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="text-[10px] font-bold uppercase tracking-[0.22em] text-muted-foreground">工作区状态</div>
            <h2 className="mt-1 font-serif text-lg font-semibold text-foreground">从导入到证据工作流</h2>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose} aria-label="收起右侧栏">
            <PanelRightClose className="h-4 w-4" />
          </Button>
        </div>
      </div>
      <ScrollArea className="flex-1">
        <div className="space-y-4 p-4">
          <div className="rounded-2xl border border-border/60 bg-card p-4">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground">Refresh</div>
              <Button variant="outline" size="sm" onClick={() => void onRefresh()}>
                刷新
              </Button>
            </div>
            <p className="text-xs leading-relaxed text-muted-foreground">
              这里汇总当前知识库从导入、索引到综述与问答的就绪状态，便于在一个固定 inspector 里查看整体上下文。
            </p>
          </div>

          {readinessItems.map((item) => (
            <div key={item.id} className="rounded-2xl border border-border/60 bg-card p-4">
              <div className="flex items-center justify-between gap-2">
                <div className="text-[10px] font-bold uppercase tracking-[0.16em] text-muted-foreground">
                  {item.title}
                </div>
                <span
                  className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                    item.priority === 'blocked'
                      ? 'bg-rose-500/10 text-rose-700'
                      : item.priority === 'active'
                        ? 'bg-blue-500/10 text-blue-700'
                        : 'bg-emerald-500/10 text-emerald-700'
                  }`}
                >
                  {item.statusLabel}
                </span>
              </div>
              <p className="mt-2 text-xs leading-relaxed text-muted-foreground">{item.reason}</p>
              <Button
                variant="ghost"
                size="sm"
                className="mt-3 justify-start px-0 text-primary"
                onClick={() => onNavigate(item.targetHref)}
              >
                <Sparkles className="h-4 w-4" />
                打开工作区
              </Button>
            </div>
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}
