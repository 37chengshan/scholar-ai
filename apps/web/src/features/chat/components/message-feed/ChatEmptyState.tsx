import { BookOpen, Lightbulb, Search, Sparkles, BarChart3, FileText } from 'lucide-react';

interface ChatEmptyStateProps {
  isZh?: boolean;
  onSuggest?: (text: string) => void;
}

const SUGGESTIONS_ZH = [
  { icon: Search, text: '帮我总结这篇论文的核心贡献', category: '论文分析' },
  { icon: BookOpen, text: '解释论文中的关键方法论', category: '论文分析' },
  { icon: Lightbulb, text: '这个研究有哪些局限性和改进空间？', category: '创意思考' },
  { icon: Sparkles, text: '和相关领域的工作相比，这篇论文的创新点是什么？', category: '知识检索' },
  { icon: BarChart3, text: '分析实验数据的统计显著性', category: '数据解读' },
  { icon: FileText, text: '帮我写一段文献综述', category: '学术写作' },
];
const SUGGESTIONS_EN = [
  { icon: Search, text: 'Summarize the key contributions of this paper', category: 'Analysis' },
  { icon: BookOpen, text: 'Explain the methodology in simple terms', category: 'Analysis' },
  { icon: Lightbulb, text: 'What are the limitations and future directions?', category: 'Ideation' },
  { icon: Sparkles, text: 'How does this compare to related work?', category: 'Retrieval' },
  { icon: BarChart3, text: 'Analyze statistical significance of results', category: 'Data' },
  { icon: FileText, text: 'Help me draft a literature review section', category: 'Writing' },
];

export function ChatEmptyState({ isZh = true, onSuggest }: ChatEmptyStateProps) {
  const suggestions = isZh ? SUGGESTIONS_ZH : SUGGESTIONS_EN;

  return (
    <div className="flex h-full min-h-[420px] flex-col justify-center px-6 py-10 lg:px-10">
      <div className="mx-auto w-full max-w-5xl">
        <div className="rounded-2xl border border-border/60 bg-background/75 p-6 backdrop-blur-sm lg:p-8">
          <div className="text-[10px] font-bold uppercase tracking-[0.3em] text-muted-foreground">
            {isZh ? '对话工作台' : 'Conversation Workspace'}
          </div>
          <h2 className="mt-3 font-serif text-3xl leading-tight text-foreground lg:text-4xl">
            {isZh ? '从一个清晰问题开始' : 'Start with a clear research question'}
          </h2>
          <p className="mt-3 max-w-3xl text-sm leading-7 text-muted-foreground lg:text-[15px]">
            {isZh
              ? '像检索页一样先聚焦目标，再逐步展开：检索证据、追问方法、抽取结论、沉淀为笔记。'
              : 'Like the search workspace, begin with a focused objective, then expand into evidence, methods, conclusions, and notes.'}
          </p>

          <div className="mt-6 grid grid-cols-1 gap-3 lg:grid-cols-2">
            {suggestions.map((s, i) => (
              <button
                key={i}
                onClick={() => onSuggest?.(s.text)}
                className="group flex items-start gap-3 rounded-xl border border-border/60 bg-paper-1 px-4 py-3 text-left transition-all hover:border-primary/20 hover:bg-primary/[0.03]"
              >
                <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-md border border-border/60 bg-paper-2 transition-colors group-hover:border-primary/20 group-hover:bg-primary/[0.06]">
                  <s.icon className="h-4 w-4 text-muted-foreground transition-colors group-hover:text-primary" />
                </div>
                <div className="min-w-0">
                  <span className="text-[10px] font-bold uppercase tracking-[0.18em] text-muted-foreground">
                    {s.category}
                  </span>
                  <p className="mt-1 text-sm leading-6 text-foreground/84">{s.text}</p>
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
