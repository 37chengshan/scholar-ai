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
    <div className="flex flex-col items-center justify-center h-full min-h-[400px] px-6 py-12">
      {/* Hero brand area */}
      <div className="relative mb-6">
        <div className="absolute inset-0 w-16 h-16 rounded-full bg-primary/20 blur-xl animate-pulse" />
        <div className="relative w-16 h-16 rounded-full bg-gradient-to-br from-primary/15 to-primary/5 flex items-center justify-center border border-primary/10">
          <Sparkles className="w-7 h-7 text-primary" />
        </div>
      </div>

      <h2 className="font-serif text-2xl font-bold text-foreground mb-2 text-center">
        {isZh ? '开始一次学术对话' : 'Start a scholarly conversation'}
      </h2>
      <p className="text-sm text-muted-foreground max-w-md leading-relaxed mb-10 text-center">
        {isZh
          ? '我可以帮你分析论文、检索知识、解读数据、辅助学术写作'
          : 'I can help you analyze papers, retrieve knowledge, interpret data, and assist with academic writing'
        }
      </p>

      {/* Suggested prompts */}
      {onSuggest && (
        <div className="w-full max-w-2xl grid grid-cols-1 sm:grid-cols-2 gap-2.5">
          {suggestions.map((s, i) => (
            <button
              key={i}
              onClick={() => onSuggest(s.text)}
              className="flex items-start gap-3 text-left px-4 py-3.5 rounded-xl border border-zinc-200/80 bg-white/80 hover:border-primary/30 hover:bg-primary/[0.03] hover:-translate-y-0.5 transition-all group shadow-sm"
            >
              <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-zinc-100 group-hover:bg-primary/10 flex items-center justify-center transition-colors">
                <s.icon className="w-4 h-4 text-zinc-400 group-hover:text-primary transition-colors" />
              </div>
              <div className="flex-1 min-w-0">
                <span className="text-[10px] uppercase tracking-widest text-zinc-400 font-medium">{s.category}</span>
                <p className="text-xs text-zinc-700 group-hover:text-foreground leading-relaxed mt-0.5 line-clamp-2">{s.text}</p>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
