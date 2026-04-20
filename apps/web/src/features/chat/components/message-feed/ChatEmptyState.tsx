import { BookOpen, Lightbulb, Search, Sparkles } from 'lucide-react';

interface ChatEmptyStateProps {
  isZh?: boolean;
  onSuggest?: (text: string) => void;
}

const SUGGESTIONS_ZH = [
  { icon: Search, text: '帮我总结这篇论文的核心贡献' },
  { icon: BookOpen, text: '解释论文中的关键方法论' },
  { icon: Lightbulb, text: '这个研究有哪些局限性和改进空间？' },
  { icon: Sparkles, text: '和相关领域的工作相比，这篇论文的创新点是什么？' },
];
const SUGGESTIONS_EN = [
  { icon: Search, text: 'Summarize the key contributions of this paper' },
  { icon: BookOpen, text: 'Explain the methodology in simple terms' },
  { icon: Lightbulb, text: 'What are the limitations and future directions?' },
  { icon: Sparkles, text: 'How does this compare to related work?' },
];

export function ChatEmptyState({ isZh = true, onSuggest }: ChatEmptyStateProps) {
  const suggestions = isZh ? SUGGESTIONS_ZH : SUGGESTIONS_EN;

  return (
    <div className="flex flex-col items-center justify-center h-full min-h-[300px] px-6 py-12 text-center">
      {/* Brand mark */}
      <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center mb-5">
        <Sparkles className="w-5 h-5 text-primary" />
      </div>

      <h2 className="font-serif text-xl font-bold text-zinc-800 mb-1.5">
        {isZh ? '开始一次学术对话' : 'Start a scholarly conversation'}
      </h2>
      <p className="text-sm text-zinc-500 max-w-sm leading-relaxed mb-8">
        {isZh
          ? '上传论文到知识库，然后选择论文或知识库后即可开始深度问答'
          : 'Upload papers to your library, select a paper or knowledge base, then start asking questions'
        }
      </p>

      {/* Suggested prompts */}
      {onSuggest && (
        <div className="w-full max-w-lg grid grid-cols-1 sm:grid-cols-2 gap-2">
          {suggestions.map((s, i) => (
            <button
              key={i}
              onClick={() => onSuggest(s.text)}
              className="flex items-start gap-2.5 text-left px-3.5 py-3 rounded-xl border border-zinc-200 bg-white hover:border-primary/40 hover:bg-primary/4 transition-all group text-xs text-zinc-600 hover:text-zinc-900 shadow-sm"
            >
              <s.icon className="w-3.5 h-3.5 text-zinc-400 group-hover:text-primary mt-0.5 flex-shrink-0 transition-colors" />
              <span className="leading-relaxed">{s.text}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
