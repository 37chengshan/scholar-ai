import { MessageSquare } from 'lucide-react';
import { Button } from '@/app/components/ui/button';

interface KnowledgeQuickAskPanelProps {
  kbId: string;
  onEnterChat: () => void;
}

export function KnowledgeQuickAskPanel({ kbId, onEnterChat }: KnowledgeQuickAskPanelProps) {
  return (
    <div className="bg-white border-2 border-zinc-900 shadow-[8px_8px_0px_0px_rgba(24,24,27,1)] p-8 space-y-4 max-w-4xl">
      <h3 className="font-serif text-2xl font-semibold">统一问答入口</h3>
      <p className="text-zinc-600 leading-relaxed">
        当前知识库问答已统一到 Chat 页面。进入后可在“快速问答 (RAG)”与“深度分析 (Agent)”之间切换，
        并保持当前知识库作用域。
      </p>
      <div className="pt-2">
        <Button onClick={onEnterChat} className="flex items-center gap-2">
          <MessageSquare className="w-4 h-4" />
          进入 Chat（全知识库作用域）
        </Button>
      </div>
      <div className="text-xs text-zinc-500">kb_id: {kbId}</div>
    </div>
  );
}
