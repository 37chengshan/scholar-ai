import { Link } from "react-router";
import {
  MessageSquare,
  Search,
  LibraryBig,
  NotebookPen,
  ArrowRight,
  Sparkles,
  FileText,
  Layers,
} from "lucide-react";
import { clsx } from "clsx";
import { useLanguage } from "../contexts/LanguageContext";
import { useAuth } from "@/contexts/AuthContext";
import { useSessions } from "@/app/hooks/useSessions";
import { useKnowledgeBases } from "@/hooks/useKnowledgeBases";

type NavCard = {
  to: string;
  icon: typeof MessageSquare;
  labelZh: string;
  labelEn: string;
  descZh: string;
  descEn: string;
  accent: string;
  badge?: { zh: string; en: string };
};

const navCards: NavCard[] = [
  {
    to: "/chat",
    icon: MessageSquare,
    labelZh: "对话",
    labelEn: "Chat",
    descZh: "与 AI 深度交流，探索文献核心观点",
    descEn: "Deep AI conversations grounded in your research",
    accent: "from-primary/10 to-primary/5",
  },
  {
    to: "/search",
    icon: Search,
    labelZh: "检索",
    labelEn: "Search",
    descZh: "全文语义检索，快速定位关键证据",
    descEn: "Semantic full-text search across your library",
    accent: "from-amber-500/10 to-amber-500/5",
  },
  {
    to: "/knowledge-bases",
    icon: LibraryBig,
    labelZh: "知识库",
    labelEn: "Library",
    descZh: "管理文献集合，构建个人研究资料库",
    descEn: "Manage collections and build your knowledge base",
    accent: "from-teal-600/10 to-teal-600/5",
  },
  {
    to: "/notes",
    icon: NotebookPen,
    labelZh: "笔记",
    labelEn: "Notes",
    descZh: "记录研究思路，整理洞见与摘录",
    descEn: "Capture insights, highlights, and annotations",
    accent: "from-violet-500/10 to-violet-500/5",
  },
];

export function Dashboard() {
  const { language } = useLanguage();
  const { user } = useAuth();
  const isZh = language === "zh";

  const { sessions } = useSessions();
  const { knowledgeBases } = useKnowledgeBases({ limit: 3, sortBy: "updated" });

  const recentSessions = sessions.slice(0, 3);

  const greeting = () => {
    const hour = new Date().getHours();
    if (isZh) {
      if (hour < 6) return "深夜好";
      if (hour < 12) return "早上好";
      if (hour < 14) return "中午好";
      if (hour < 18) return "下午好";
      return "晚上好";
    } else {
      if (hour < 12) return "Good morning";
      if (hour < 18) return "Good afternoon";
      return "Good evening";
    }
  };

  const userName = user?.name?.split(/\s+/)[0] || (isZh ? "研究者" : "Scholar");

  return (
    <div className="h-full overflow-y-auto bg-background">
      <div className="mx-auto max-w-5xl px-6 py-8 lg:px-10 lg:py-10">

        {/* Header */}
        <div className="mb-10 border-b border-foreground/10 pb-8">
          <div className="mb-1 text-[10px] font-bold uppercase tracking-[0.3em] text-primary">
            ScholarAI
          </div>
          <h1 className="font-serif text-3xl font-bold tracking-tight text-foreground lg:text-4xl">
            {greeting()}，{userName}
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            {isZh
              ? "今天想研究什么？从下方选择一个工作区开始。"
              : "What are you researching today? Choose a workspace below."}
          </p>
        </div>

        {/* Main Nav Cards */}
        <section className="mb-10">
          <div className="mb-4 flex items-center gap-2">
            <Layers className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-[10px] font-bold uppercase tracking-[0.25em] text-muted-foreground">
              {isZh ? "工作区" : "Workspaces"}
            </span>
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {navCards.map((card) => (
              <Link
                key={card.to}
                to={card.to}
                className={clsx(
                  "group relative flex flex-col gap-3 overflow-hidden rounded-lg border border-foreground/10 bg-card p-5 text-left",
                  "transition-[transform,border-color,box-shadow] duration-200 hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-md",
                )}
              >
                <div className={clsx("absolute inset-0 bg-gradient-to-br opacity-0 transition-opacity duration-200 group-hover:opacity-100", card.accent)} />
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

            {/* Quick new chat card */}
            <Link
              to="/chat?new=1"
              className={clsx(
                "group relative flex flex-col gap-3 overflow-hidden rounded-lg border border-dashed border-primary/30 bg-primary/[0.03] p-5 text-left",
                "transition-[transform,border-color,background-color] duration-200 hover:-translate-y-0.5 hover:border-primary/50 hover:bg-primary/[0.06]",
              )}
            >
              <div className="flex items-start justify-between">
                <div className="flex h-9 w-9 items-center justify-center rounded-md border border-primary/20 bg-primary/10">
                  <Sparkles className="h-4 w-4 text-primary" />
                </div>
                <ArrowRight className="h-4 w-4 translate-x-1 text-transparent opacity-0 transition-[transform,opacity,color] duration-200 group-hover:translate-x-0 group-hover:text-primary group-hover:opacity-100" />
              </div>
              <div>
                <div className="font-serif text-base font-semibold text-primary">
                  {isZh ? "新对话" : "New Chat"}
                </div>
                <p className="mt-1 text-[12px] leading-relaxed text-muted-foreground">
                  {isZh ? "立即开启一次全新的 AI 研究对话" : "Start a fresh AI research conversation"}
                </p>
              </div>
            </Link>
          </div>
        </section>

        {/* Recent Activity */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">

          {/* Recent Conversations */}
          {recentSessions.length > 0 && (
            <section>
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <MessageSquare className="h-3.5 w-3.5 text-muted-foreground" />
                  <span className="text-[10px] font-bold uppercase tracking-[0.25em] text-muted-foreground">
                    {isZh ? "最近对话" : "Recent Chats"}
                  </span>
                </div>
                <Link
                  to="/chat"
                  className="flex items-center gap-1 text-[11px] text-muted-foreground/60 transition-colors hover:text-primary"
                >
                  {isZh ? "全部" : "All"}
                  <ArrowRight className="h-3 w-3" />
                </Link>
              </div>
              <div className="space-y-1.5">
                {recentSessions.map((session) => (
                  <Link
                    key={session.id}
                    to={`/chat?session=${session.id}`}
                    className="group flex w-full items-center gap-3 rounded-md border border-foreground/8 bg-card px-3.5 py-3 text-left transition-colors hover:border-primary/20 hover:bg-muted/30"
                  >
                    <FileText className="h-3.5 w-3.5 shrink-0 text-muted-foreground/50" />
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-[12.5px] font-medium text-foreground">
                        {session.title}
                      </div>
                      <div className="mt-0.5 text-[10px] text-muted-foreground">
                        {session.messageCount}{isZh ? " 条消息" : " messages"}
                      </div>
                    </div>
                    <ArrowRight className="h-3.5 w-3.5 shrink-0 text-transparent transition-colors group-hover:text-primary/50" />
                  </Link>
                ))}
              </div>
            </section>
          )}

          {/* Recent Knowledge Bases */}
          {knowledgeBases.length > 0 && (
            <section>
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <LibraryBig className="h-3.5 w-3.5 text-muted-foreground" />
                  <span className="text-[10px] font-bold uppercase tracking-[0.25em] text-muted-foreground">
                    {isZh ? "知识库" : "Collections"}
                  </span>
                </div>
                <Link
                  to="/knowledge-bases"
                  className="flex items-center gap-1 text-[11px] text-muted-foreground/60 transition-colors hover:text-primary"
                >
                  {isZh ? "全部" : "All"}
                  <ArrowRight className="h-3 w-3" />
                </Link>
              </div>
              <div className="space-y-1.5">
                {knowledgeBases.map((kb) => (
                  <Link
                    key={kb.id}
                    to={`/knowledge-bases/${kb.id}`}
                    className="group flex w-full items-center gap-3 rounded-md border border-foreground/8 bg-card px-3.5 py-3 text-left transition-colors hover:border-primary/20 hover:bg-muted/30"
                  >
                    <LibraryBig className="h-3.5 w-3.5 shrink-0 text-muted-foreground/50" />
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-[12.5px] font-medium text-foreground">
                        {kb.name}
                      </div>
                      <div className="mt-0.5 text-[10px] text-muted-foreground">
                        {kb.paperCount}{isZh ? " 篇文献" : " papers"}
                      </div>
                    </div>
                    <ArrowRight className="h-3.5 w-3.5 shrink-0 text-transparent transition-colors group-hover:text-primary/50" />
                  </Link>
                ))}
              </div>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}
