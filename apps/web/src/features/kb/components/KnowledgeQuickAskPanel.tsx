import { MessageSquare } from 'lucide-react';
import { Button } from '@/app/components/ui/button';

interface KnowledgeQuickAskPanelProps {
  kbId: string;
  onEnterChat: () => void;
}

export function KnowledgeQuickAskPanel({ kbId, onEnterChat }: KnowledgeQuickAskPanelProps) {
  return (
    <div className="max-w-4xl space-y-4 border border-border/80 bg-paper-1 p-8">
      <h3 className="font-serif text-2xl font-semibold">统一问答入口</h3>
      <p className="text-muted-foreground leading-relaxed">
        当前知识库问答已统一到 Chat 页面。进入后可在“快速问答 (RAG)”与“深度分析 (Agent)”之间切换，
        并保持当前知识库作用域。
      </p>
      <div className="pt-2">
        <Button onClick={onEnterChat} className="flex items-center gap-2">
          <MessageSquare className="w-4 h-4" />
          进入 Chat（全知识库作用域）
        </Button>
      </div>
      <div className="text-xs text-muted-foreground">kb_id: {kbId}</div>
    </div>
  );
}
