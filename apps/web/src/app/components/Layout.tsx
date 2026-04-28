import { useEffect, useMemo, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router";
import {
  BookOpen,
  LayoutDashboard,
  LibraryBig,
  LogOut,
  Menu,
  MessageSquarePlus,
  MessagesSquare,
  NotebookPen,
  PanelLeftClose,
  PanelLeftOpen,
  Search,
  Settings,
  TrendingUp,
} from "lucide-react";
import { clsx } from "clsx";
import { useLanguage } from "../contexts/LanguageContext";
import { Logo } from "./landing/Logo";
import { Avatar, AvatarFallback, AvatarImage } from "./ui/avatar";
import { useAuth } from "@/contexts/AuthContext";
import { Sheet, SheetContent } from "./ui/sheet";
import { useSessions } from "@/app/hooks/useSessions";
import { useKnowledgeBases } from "@/hooks/useKnowledgeBases";
import type { ChatSession } from "@/app/hooks/useSessions";

type WorkspaceItem = {
  to: string;
  icon: typeof Search;
  labelZh: string;
  labelEn: string;
};

const workspaceItems: WorkspaceItem[] = [
  {
    to: "/dashboard",
    icon: LayoutDashboard,
    labelZh: "总览",
    labelEn: "Overview",
  },
  {
    to: "/analytics",
    icon: TrendingUp,
    labelZh: "看板",
    labelEn: "Analytics",
  },
  {
    to: "/chat",
    icon: MessagesSquare,
    labelZh: "对话",
    labelEn: "Chat",
  },
  {
    to: "/search",
    icon: Search,
    labelZh: "检索",
    labelEn: "Search",
  },
  {
    to: "/knowledge-bases",
    icon: LibraryBig,
    labelZh: "知识库",
    labelEn: "Library",
  },
  {
    to: "/notes",
    icon: NotebookPen,
    labelZh: "笔记",
    labelEn: "Notes",
  },
];

function startOfDay(d: Date) {
  const c = new Date(d);
  c.setHours(0, 0, 0, 0);
  return c;
}

type DateGroup = { label: string; sessions: ChatSession[] };

function groupSessionsByDate(sessions: ChatSession[], isZh: boolean): DateGroup[] {
  const now = new Date();
  const todayStart = startOfDay(now);
  const weekAgo = new Date(todayStart);
  weekAgo.setDate(weekAgo.getDate() - 6);
  const monthAgo = new Date(todayStart);
  monthAgo.setDate(monthAgo.getDate() - 30);

  const buckets: DateGroup[] = [
    { label: isZh ? "今天" : "Today", sessions: [] },
    { label: isZh ? "本周" : "This Week", sessions: [] },
    { label: isZh ? "本月" : "This Month", sessions: [] },
    { label: isZh ? "更早" : "Older", sessions: [] },
  ];

  for (const s of sessions) {
    const d = new Date(s.updatedAt || s.createdAt);
    if (d >= todayStart) buckets[0].sessions.push(s);
    else if (d >= weekAgo) buckets[1].sessions.push(s);
    else if (d >= monthAgo) buckets[2].sessions.push(s);
    else buckets[3].sessions.push(s);
  }

  return buckets.filter((bucket) => bucket.sessions.length > 0);
}

function formatMetaDate(value?: string, locale = "zh-CN") {
  if (!value) return "—";
  try {
    return new Intl.DateTimeFormat(locale, { month: "short", day: "numeric" }).format(new Date(value));
  } catch {
    return value;
  }
}

function getUserInitials(name?: string | null) {
  if (!name) return "SA";
  const parts = name
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2);

  if (parts.length === 0) return "SA";
  return parts.map((part) => part[0]?.toUpperCase() ?? "").join("");
}

const LEFT_SIDEBAR_STORAGE_KEY = "scholarai-left-sidebar-collapsed";

export function Layout() {
  const { language } = useLanguage();
  const { logout, user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [leftCollapsed, setLeftCollapsed] = useState(false);
  const isZh = language === "zh";
  const locale = isZh ? "zh-CN" : "en-US";
  const currentQuery = new URLSearchParams(location.search);
  const activeSessionId = currentQuery.get("session");

  const { sessions, currentSession, loading: sessionsLoading } = useSessions();
  const { knowledgeBases } = useKnowledgeBases({ limit: 5, sortBy: "updated" });

  const sortedSessions = useMemo(
    () =>
      [...sessions].sort((a, b) => {
        const ta = new Date(a.updatedAt || a.createdAt).getTime();
        const tb = new Date(b.updatedAt || b.createdAt).getTime();
        return tb - ta;
      }),
    [sessions],
  );

  const dateGroups = useMemo(
    () => groupSessionsByDate(sortedSessions, isZh),
    [sortedSessions, isZh],
  );

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(LEFT_SIDEBAR_STORAGE_KEY);
      setLeftCollapsed(stored === "1");
    } catch {
      setLeftCollapsed(false);
    }
  }, []);

  useEffect(() => {
    try {
      window.localStorage.setItem(LEFT_SIDEBAR_STORAGE_KEY, leftCollapsed ? "1" : "0");
    } catch {
      // Ignore storage failures.
    }
  }, [leftCollapsed]);

  const handleLogout = async () => {
    await logout();
    navigate("/");
  };

  const handleNewChat = () => {
    navigate("/chat?new=1");
    setMobileMenuOpen(false);
  };

  const handleOpenSession = (sessionId: string) => {
    navigate(`/chat?session=${sessionId}`);
    setMobileMenuOpen(false);
  };

  const SidebarContent = (
    <div className="z-20 flex h-full flex-col border-r-2 border-border/70 bg-gradient-to-b from-muted/40 to-background shadow-2xl">
      <div className={clsx("shrink-0 border-b border-border/50", leftCollapsed ? "px-3 pt-5 pb-4" : "px-5 pt-6 pb-4")}>
        {leftCollapsed ? (
          <div className="flex justify-center">
            <button
              type="button"
              onClick={() => setLeftCollapsed(false)}
              className="inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-border/60 bg-background text-foreground/65 transition-colors hover:border-primary/25 hover:text-primary"
              aria-label={isZh ? "展开左侧栏" : "Expand sidebar"}
              title={isZh ? "展开左侧栏" : "Expand sidebar"}
            >
              <PanelLeftOpen className="h-4 w-4" />
            </button>
          </div>
        ) : (
          <div className="flex items-start justify-between gap-3">
            <button
              type="button"
              onClick={() => {
                navigate("/dashboard");
                setMobileMenuOpen(false);
              }}
              className="group flex min-w-0 items-center gap-3 text-left transition-colors"
            >
              <Logo
                className="min-w-0 gap-2.5"
                markSize={34}
                textClassName="text-[1.65rem] leading-none"
              />
              <div className="ml-auto flex items-center gap-1.5">
                <span className="relative flex h-2.5 w-2.5">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary/40" />
                  <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-primary/70" />
                </span>
              </div>
            </button>
          </div>
        )}

        <div className={clsx("mt-5 flex items-center", leftCollapsed ? "justify-center" : "justify-between gap-3")}>
          <button
            type="button"
            onClick={handleNewChat}
            title={isZh ? "新对话" : "New Thread"}
            className={clsx(
              "inline-flex items-center transition-colors hover:text-primary",
              leftCollapsed
                ? "h-10 w-10 justify-center rounded-full border border-border/60 bg-background text-foreground"
                : "gap-2 border-b border-border/70 pb-1 text-[11px] font-bold uppercase tracking-[0.22em] text-foreground hover:border-primary",
            )}
          >
            <MessageSquarePlus className="h-3.5 w-3.5" />
            {!leftCollapsed ? (isZh ? "新对话" : "New Thread") : null}
          </button>
          {!leftCollapsed ? (
            <button
              type="button"
              onClick={() => setLeftCollapsed(true)}
              className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border border-border/60 bg-background text-foreground/65 transition-colors hover:border-primary/25 hover:text-primary"
              aria-label={isZh ? "收起左侧栏" : "Collapse sidebar"}
              title={isZh ? "收起左侧栏" : "Collapse sidebar"}
            >
              <PanelLeftClose className="h-4 w-4" />
            </button>
          ) : null}
        </div>
      </div>

      <div className={clsx("shrink-0 border-b border-border/60", leftCollapsed ? "px-2 py-3" : "px-5 py-4")}>
        {!leftCollapsed ? (
          <div className="mb-3 text-[10px] font-semibold text-muted-foreground/80">
            {isZh ? "工作区" : "Workspace"}
          </div>
        ) : null}
        <div className={clsx(leftCollapsed ? "space-y-1" : "space-y-0.5")}>
          {workspaceItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={() => setMobileMenuOpen(false)}
              title={isZh ? item.labelZh : item.labelEn}
              className={({ isActive }) =>
                clsx(
                  "group flex items-center transition-colors",
                  isActive
                    ? "bg-primary/[0.07] text-foreground"
                    : "text-muted-foreground hover:bg-muted/50 hover:text-foreground",
                  leftCollapsed
                    ? "h-10 justify-center rounded-xl border border-transparent px-0"
                    : "h-10 gap-2 rounded-xl px-3",
                )
              }
            >
              {({ isActive }) => (
                <>
                  <item.icon className={clsx("h-3.5 w-3.5 shrink-0", isActive ? "text-primary" : "text-foreground/55 group-hover:text-foreground/75")} />
                  {!leftCollapsed ? (
                    <div className={clsx("text-[var(--font-xs)] font-semibold tracking-[0.04em]", isActive ? "text-foreground" : "text-foreground/82")}>
                      {isZh ? item.labelZh : item.labelEn}
                    </div>
                  ) : null}
                </>
              )}
            </NavLink>
          ))}
        </div>
      </div>

      <div className={clsx("min-h-0 flex-1 overflow-y-auto", leftCollapsed ? "px-2 py-3" : "px-5 py-4")}>
        {!leftCollapsed ? (
        <section>
          {!leftCollapsed ? (
            <div className="mb-2 flex items-center justify-between px-2">
              <span className="flex items-center gap-1.5 text-[9px] font-bold uppercase tracking-[0.28em] text-muted-foreground">
                <MessagesSquare className="h-3 w-3" />
                {isZh ? "最近对话" : "Recent Threads"}
              </span>
              <button
                type="button"
                onClick={() => {
                  navigate("/dashboard");
                  setMobileMenuOpen(false);
                }}
                className="text-[10px] text-muted-foreground/70 transition-colors hover:text-primary"
              >
                {isZh ? "进入" : "Open"}
              </button>
            </div>
          ) : null}

          {sessionsLoading ? (
            <div className={clsx("text-xs text-muted-foreground", leftCollapsed ? "px-0 py-3 text-center" : "px-2 py-3")}>
              {isZh ? "载入中…" : "Loading…"}
            </div>
          ) : dateGroups.length > 0 ? (
            <div className={clsx(leftCollapsed ? "space-y-1" : "space-y-4")}>
              {dateGroups.slice(0, 2).map((group) => (
                <div key={group.label}>
                  {!leftCollapsed ? (
                    <div className="mb-1 border-b border-border/60 px-0 pb-1 text-[9px] font-semibold text-muted-foreground/70">
                      {group.label}
                    </div>
                  ) : null}
                  <div className="space-y-0.5">
                    {group.sessions.slice(0, 3).map((session) => {
                      const isActive =
                        location.pathname.startsWith("/chat") &&
                        (activeSessionId ? activeSessionId === session.id : currentSession?.id === session.id);

                      return (
                        <button
                          key={session.id}
                          type="button"
                          onClick={() => handleOpenSession(session.id)}
                          title={session.title}
                          className={clsx(
                            "group w-full text-left transition-all duration-150",
                            leftCollapsed
                              ? "flex h-10 items-center justify-center rounded-2xl border border-transparent px-0 py-0"
                              : "rounded-lg px-2.5 py-2",
                            isActive
                              ? leftCollapsed
                                ? "border-primary/30 bg-primary/[0.06]"
                                : "bg-primary/[0.03]"
                              : leftCollapsed
                                ? "hover:border-border/80 hover:bg-background"
                                : "hover:bg-primary/[0.02]",
                          )}
                        >
                          {leftCollapsed ? (
                            <MessagesSquare className={clsx("h-3.5 w-3.5", isActive ? "text-primary" : "text-foreground/60")} />
                          ) : (
                            <>
                              <div className="line-clamp-1 text-[var(--font-xs)] font-medium leading-snug text-foreground">
                                {session.title}
                              </div>
                              <div className="mt-1 flex items-center gap-1.5 text-[10px] text-muted-foreground">
                                <span>{formatMetaDate(session.updatedAt || session.createdAt, locale)}</span>
                                <span className="text-border">·</span>
                                <span>{session.messageCount}{isZh ? " 条" : " msg"}</span>
                              </div>
                            </>
                          )}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className={clsx(
              "text-xs leading-5 text-muted-foreground",
              leftCollapsed ? "px-0 py-2 text-center" : "border-l border-border/70 px-3 py-2",
            )}>
              {leftCollapsed ? "…" : isZh ? "还没有历史对话，点击上方按钮开始。" : "No threads yet. Start one from the primary action above."}
            </div>
          )}
        </section>
        ) : null}

        {!leftCollapsed && knowledgeBases.length > 0 && (
          <section className={clsx(leftCollapsed ? "mt-4" : "mt-6")}>
            {!leftCollapsed ? (
              <div className="mb-2 flex items-center justify-between px-2">
                <span className="flex items-center gap-1.5 text-[9px] font-bold uppercase tracking-[0.28em] text-muted-foreground">
                  <BookOpen className="h-3 w-3" />
                  {isZh ? "资料馆藏" : "Collections"}
                </span>
                <button
                  type="button"
                  onClick={() => {
                    navigate("/knowledge-bases");
                    setMobileMenuOpen(false);
                  }}
                  className="text-[10px] text-muted-foreground/70 transition-colors hover:text-primary"
                >
                  {isZh ? "进入" : "Open"}
                </button>
              </div>
            ) : null}
            <div className="space-y-0.5">
              {knowledgeBases.slice(0, 3).map((kb) => (
                <button
                  key={kb.id}
                  type="button"
                  onClick={() => {
                    navigate(`/knowledge-bases/${kb.id}`);
                    setMobileMenuOpen(false);
                  }}
                  title={kb.name}
                  className={clsx(
                    "group flex w-full text-left transition-colors",
                    leftCollapsed
                      ? "h-10 items-center justify-center rounded-2xl border border-transparent px-0 py-0"
                      : "items-start gap-2 border-l border-transparent px-0 py-2 pl-3 hover:border-border/80",
                    leftCollapsed && "hover:border-border/80 hover:bg-background",
                  )}
                >
                  <BookOpen className={clsx("h-3.5 w-3.5 shrink-0 text-foreground/55 group-hover:text-foreground/70 transition-colors", !leftCollapsed && "mt-0.5")} />
                  {!leftCollapsed ? (
                    <div className="min-w-0">
                      <div className="truncate text-[11.5px] font-medium text-foreground">
                        {kb.name}
                      </div>
                      <div className="mt-1 text-[10px] text-muted-foreground">
                        {kb.paperCount}{isZh ? " 篇论文" : " papers"}
                      </div>
                    </div>
                  ) : null}
                </button>
              ))}
            </div>
          </section>
        )}
      </div>

      <div className={clsx("shrink-0 border-t border-border/60 bg-primary/[0.01]", leftCollapsed ? "px-2 pb-3 pt-3" : "px-3 pb-4 pt-3")}>
        <div className={clsx("flex items-center", leftCollapsed ? "flex-col gap-2 px-0 py-0" : "gap-2 px-2 py-2")}>
          <Avatar className="h-8 w-8 shrink-0 rounded-md border border-border/70 bg-card shadow-sm">
            <AvatarImage src={user?.avatar ?? undefined} alt={user?.name || "User"} className="object-cover" />
            <AvatarFallback className="rounded-md bg-muted font-sans text-[10px] font-bold uppercase tracking-[0.18em] text-foreground/70">
              {getUserInitials(user?.name)}
            </AvatarFallback>
          </Avatar>
          {!leftCollapsed ? (
            <div className="min-w-0 flex-1">
              <div className="text-[8.5px] font-bold uppercase tracking-[0.18em] text-muted-foreground/80">
                {isZh ? "账号" : "Profile"}
              </div>
              <div className="truncate text-[12.5px] font-semibold leading-tight text-foreground/90">
                {user?.name || (isZh ? "研究者" : "Scholar")}
              </div>
            </div>
          ) : null}
          <button
            type="button"
            onClick={() => {
              navigate("/settings");
              setMobileMenuOpen(false);
            }}
            title={isZh ? "打开设置" : "Open settings"}
            className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-xl border border-border/60 bg-background text-foreground/60 transition-all duration-150 hover:border-primary/25 hover:text-primary hover:bg-primary/[0.04]"
            aria-label={isZh ? "打开设置" : "Open settings"}
          >
            <Settings className="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            onClick={handleLogout}
            title={isZh ? "退出登录" : "Log out"}
            className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-xl border border-border/60 bg-paper-2 text-foreground/60 transition-colors hover:border-primary/20 hover:text-primary"
            aria-label={isZh ? "退出登录" : "Log out"}
          >
            <LogOut className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <div className="relative flex h-dvh overflow-hidden bg-background text-foreground antialiased">
      <aside className={clsx(
        "hidden shrink-0 border-r-2 border-border/70 bg-gradient-to-b from-muted/40 to-background shadow-2xl transition-[width] duration-200 md:block",
        leftCollapsed ? "w-[var(--sidebar-collapsed)]" : "w-[var(--sidebar-expanded)]",
      )}>
        {SidebarContent}
      </aside>

      <div className="relative flex min-w-0 flex-1 overflow-hidden bg-background">
        <div className="pointer-events-none absolute inset-x-0 top-0 z-20 flex items-center justify-between px-4 pt-4 md:hidden">
          <button
            type="button"
            onClick={() => setMobileMenuOpen(true)}
            className="pointer-events-auto inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-border/60 bg-paper-1/90 text-foreground/72 backdrop-blur-md"
            aria-label={isZh ? "打开导航" : "Open navigation"}
          >
            <Menu className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={() => navigate("/settings")}
            className="pointer-events-auto inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-border/60 bg-paper-1/90 text-foreground/72 backdrop-blur-md"
            aria-label={isZh ? "打开设置" : "Open settings"}
          >
            <Settings className="h-4 w-4" />
          </button>
        </div>

        <main className="relative min-h-0 flex-1 overflow-hidden pt-16 md:pt-0">
          <Outlet />
        </main>
      </div>

      <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
        <SheetContent side="left" className="w-[292px] border-r border-border/60 bg-paper-2 p-0">
          {SidebarContent}
        </SheetContent>
      </Sheet>
    </div>
  );
}
