import { Link } from 'react-router';
import {
  ArrowRight,
  BookOpen,
  Compass,
  FileSearch,
  Layers,
  LibraryBig,
  Loader2,
  MessageSquare,
  NotebookPen,
  Sparkles,
} from 'lucide-react';
import { clsx } from 'clsx';
import { useLanguage } from '../contexts/LanguageContext';
import { useAuth } from '@/contexts/AuthContext';
import { useResearchCommandCenter } from '@/features/workflow/hooks/useResearchCommandCenter';
import type { ResearchCommandItem } from '@/features/workflow/commandCenter';

type NavCard = {
  to: string;
  icon: typeof MessageSquare;
  labelZh: string;
  labelEn: string;
  descZh: string;
  descEn: string;
  accent: string;
};

const navCards: NavCard[] = [
  {
    to: '/search',
    icon: FileSearch,
    labelZh: 'Search',
    labelEn: 'Search',
    descZh: '发现论文、导入知识库、继续研究链',
    descEn: 'Discover papers and move them into the research loop',
    accent: 'from-amber-500/10 to-amber-500/5',
  },
  {
    to: '/knowledge-bases',
    icon: LibraryBig,
    labelZh: 'Knowledge Base',
    labelEn: 'Knowledge Base',
    descZh: '查看导入状态、索引状态和 readiness',
    descEn: 'Track imports, indexing, and readiness',
    accent: 'from-teal-600/10 to-teal-600/5',
  },
  {
    to: '/chat',
    icon: MessageSquare,
    labelZh: 'Chat',
    labelEn: 'Chat',
    descZh: '围绕当前证据继续提问和写结论',
    descEn: 'Continue reasoning on top of current evidence',
    accent: 'from-primary/10 to-primary/5',
  },
  {
    to: '/notes',
    icon: NotebookPen,
    labelZh: 'Notes',
    labelEn: 'Notes',
    descZh: '沉淀证据、观点与后续行动',
    descEn: 'Capture evidence, conclusions, and next steps',
    accent: 'from-violet-500/10 to-violet-500/5',
  },
];

const categoryMeta: Record<
  ResearchCommandItem['category'],
  {
    icon: typeof MessageSquare;
    accent: string;
    labelZh: string;
    labelEn: string;
  }
> = {
  chat: {
    icon: MessageSquare,
    accent: 'from-primary/12 to-primary/5',
    labelZh: '继续中的 Chat',
    labelEn: 'Chat in Progress',
  },
  kb: {
    icon: LibraryBig,
    accent: 'from-teal-600/12 to-teal-600/5',
    labelZh: '处理中 Knowledge Base',
    labelEn: 'Knowledge Base',
  },
  read: {
    icon: BookOpen,
    accent: 'from-amber-500/12 to-amber-500/5',
    labelZh: '最近可继续阅读',
    labelEn: 'Resume Reading',
  },
  review: {
    icon: Compass,
    accent: 'from-rose-500/12 to-rose-500/5',
    labelZh: 'Review / Compare',
    labelEn: 'Review / Compare',
  },
  compare: {
    icon: Compass,
    accent: 'from-rose-500/12 to-rose-500/5',
    labelZh: 'Review / Compare',
    labelEn: 'Review / Compare',
  },
};

function CommandCard({ item, isZh }: { item: ResearchCommandItem; isZh: boolean }) {
  const meta = categoryMeta[item.category];
  const Icon = meta.icon;

  return (
    <Link
      to={item.targetHref}
      className="group relative overflow-hidden rounded-xl border border-border/70 bg-card p-5 transition-[transform,border-color,box-shadow] duration-200 hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-md"
    >
      <div className={clsx('absolute inset-0 bg-gradient-to-br opacity-0 transition-opacity duration-200 group-hover:opacity-100', meta.accent)} />
      <div className="relative flex items-start justify-between gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-border/70 bg-background/85">
          <Icon className="h-4 w-4 text-foreground/70" />
        </div>
        <span
          className={clsx(
            'rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.16em]',
            item.priority === 'blocked' && 'border-rose-500/30 bg-rose-500/10 text-rose-700',
            item.priority === 'active' && 'border-blue-500/30 bg-blue-500/10 text-blue-700',
            item.priority === 'ready' && 'border-emerald-500/30 bg-emerald-500/10 text-emerald-700',
            item.priority === 'recent' && 'border-amber-500/30 bg-amber-500/10 text-amber-700',
          )}
        >
          {item.statusLabel}
        </span>
      </div>

      <div className="relative mt-4">
        <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground">
          {isZh ? meta.labelZh : meta.labelEn}
        </div>
        <h3 className="mt-2 font-serif text-xl font-semibold tracking-tight text-foreground">
          {item.title}
        </h3>
        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{item.reason}</p>
      </div>

      <div className="relative mt-5 flex items-center justify-between border-t border-border/60 pt-3 text-[11px] text-muted-foreground">
        <span>{isZh ? '打开对应工作区继续处理' : 'Open the destination workspace to continue'}</span>
        <span className="inline-flex items-center gap-1 font-semibold text-foreground/75 transition-colors group-hover:text-primary">
          {isZh ? '继续' : 'Continue'}
          <ArrowRight className="h-3.5 w-3.5" />
        </span>
      </div>
    </Link>
  );
}

export function Dashboard() {
  const { language } = useLanguage();
  const { user } = useAuth();
  const isZh = language === 'zh';
  const { commands, loading } = useResearchCommandCenter();

  const greeting = () => {
    const hour = new Date().getHours();
    if (isZh) {
      if (hour < 6) return '深夜好';
      if (hour < 12) return '早上好';
      if (hour < 14) return '中午好';
      if (hour < 18) return '下午好';
      return '晚上好';
    }
    if (hour < 12) return 'Good morning';
    if (hour < 18) return 'Good afternoon';
    return 'Good evening';
  };

  const userName = user?.name?.split(/\s+/)[0] || (isZh ? '研究者' : 'Scholar');

  return (
    <div className="h-full overflow-y-auto bg-background">
      <div className="mx-auto max-w-6xl px-6 py-8 lg:px-10 lg:py-10">
        <div className="mb-10 border-b border-foreground/10 pb-8">
          <div className="mb-1 text-[10px] font-bold uppercase tracking-[0.3em] text-primary">
            ScholarAI
          </div>
          <h1 className="font-serif text-3xl font-bold tracking-tight text-foreground lg:text-4xl">
            {greeting()}，{userName}
          </h1>
          <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
            {isZh
              ? '这里不是执行页，而是研究指挥台。先看当前卡在哪里，再跳到对应页面继续完成。'
              : 'This is a command center, not an execution page. Check what is blocked or ready, then jump into the right workspace.'}
          </p>
        </div>

        <section className="mb-10">
          <div className="mb-4 flex items-center gap-2">
            <Layers className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-[10px] font-bold uppercase tracking-[0.25em] text-muted-foreground">
              {isZh ? '下一步动作' : 'Next Actions'}
            </span>
          </div>

          {loading ? (
            <div className="flex min-h-[220px] items-center justify-center rounded-xl border border-border/70 bg-card">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                {isZh ? '正在整理研究链状态...' : 'Building your research command center...'}
              </div>
            </div>
          ) : commands.length > 0 ? (
            <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
              {commands.map((item) => (
                <CommandCard key={item.id} item={item} isZh={isZh} />
              ))}
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-border/70 bg-card p-6">
              <div className="flex items-start gap-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-primary/20 bg-primary/10">
                  <Sparkles className="h-4 w-4 text-primary" />
                </div>
                <div className="space-y-4">
                  <div>
                    <h2 className="font-serif text-xl font-semibold text-foreground">
                      {isZh ? '从第一条研究链开始' : 'Start your first research loop'}
                    </h2>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {isZh
                        ? '先搜索论文，再放进 Knowledge Base，最后带着证据进入 Chat。'
                        : 'Search first, move papers into a knowledge base, then continue in Chat with evidence.'}
                    </p>
                  </div>
                  <div className="grid gap-3 md:grid-cols-3">
                    {[
                      {
                        title: isZh ? '1. Search' : '1. Search',
                        body: isZh ? '从检索页发现论文，并判断哪些值得纳入当前研究流。' : 'Discover papers and decide which ones belong in the current loop.',
                        href: '/search',
                      },
                      {
                        title: isZh ? '2. Add to KB' : '2. Add to KB',
                        body: isZh ? '把有价值的结果放进 Knowledge Base，观察导入和索引状态。' : 'Move promising results into a knowledge base and watch readiness.',
                        href: '/knowledge-bases',
                      },
                      {
                        title: isZh ? '3. Ask in Chat' : '3. Ask in Chat',
                        body: isZh ? '当证据 ready 后，把问题带进 Chat 继续分析和写作。' : 'Once evidence is ready, continue reasoning and drafting in Chat.',
                        href: '/chat',
                      },
                    ].map((step) => (
                      <Link
                        key={step.title}
                        to={step.href}
                        className="rounded-lg border border-border/60 bg-background/70 p-4 transition-colors hover:border-primary/30 hover:bg-primary/[0.03]"
                      >
                        <div className="font-medium text-foreground">{step.title}</div>
                        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{step.body}</p>
                      </Link>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </section>

        <section>
          <div className="mb-4 flex items-center gap-2">
            <Layers className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-[10px] font-bold uppercase tracking-[0.25em] text-muted-foreground">
              {isZh ? '轻入口' : 'Light Entry Points'}
            </span>
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {navCards.map((card) => (
              <Link
                key={card.to}
                to={card.to}
                className="group relative flex flex-col gap-3 overflow-hidden rounded-lg border border-foreground/10 bg-card p-5 text-left transition-[transform,border-color,box-shadow] duration-200 hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-md"
              >
                <div className={clsx('absolute inset-0 bg-gradient-to-br opacity-0 transition-opacity duration-200 group-hover:opacity-100', card.accent)} />
                <div className="relative flex items-start justify-between">
                  <div className="flex h-9 w-9 items-center justify-center rounded-md border border-foreground/8 bg-muted">
                    <card.icon className="h-4 w-4 text-foreground/60" />
                  </div>
                  <ArrowRight className="h-4 w-4 translate-x-1 text-transparent opacity-0 transition-[transform,opacity,color] duration-200 group-hover:translate-x-0 group-hover:text-primary group-hover:opacity-100" />
                </div>
                <div className="relative">
                  <div className="font-serif text-base font-semibold text-foreground">
                    {isZh ? card.labelZh : card.labelEn}
                  </div>
                  <p className="mt-1 text-[12px] leading-relaxed text-muted-foreground">
                    {isZh ? card.descZh : card.descEn}
                  </p>
                </div>
              </Link>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
