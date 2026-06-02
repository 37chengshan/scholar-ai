import { useMemo } from "react";
import { Link, NavLink } from "react-router";
import {
  BookOpen,
  LayoutDashboard,
  LibraryBig,
  MessageSquarePlus,
  MessagesSquare,
  NotebookPen,
  PanelLeftClose,
  PanelLeftOpen,
  Search,
  TrendingUp,
} from "lucide-react";
import { clsx } from "clsx";
import { Logo } from "../landing/Logo";
import { ScrollArea } from "../ui/scroll-area";
import { useSessions } from "@/app/hooks/useSessions";
import { useKnowledgeBases } from "@/hooks/useKnowledgeBases";
import { getKnowledgeBaseDisplayMetadata } from "@/app/lib/knowledgeBaseDisplay";
import { SessionList } from "./SessionList";
import { UserProfile } from "./UserProfile";

type WorkspaceItem = {
  to: string;
  icon: typeof Search;
  labelZh: string;
  labelEn: string;
};

const workspaceItems: WorkspaceItem[] = [
  { to: "/dashboard", icon: LayoutDashboard, labelZh: "总览", labelEn: "Overview" },
  { to: "/analytics", icon: TrendingUp, labelZh: "看板", labelEn: "Analytics" },
  { to: "/chat", icon: MessagesSquare, labelZh: "对话", labelEn: "Chat" },
  { to: "/search", icon: Search, labelZh: "检索", labelEn: "Search" },
  { to: "/knowledge-bases", icon: LibraryBig, labelZh: "知识库", labelEn: "Library" },
  { to: "/notes", icon: NotebookPen, labelZh: "笔记", labelEn: "Notes" },
];

const PRIMARY_WORKSPACE_ITEMS = ["/dashboard", "/search", "/chat"];

interface SidebarContentProps {
  isZh: boolean;
  locale: string;
  leftCollapsed: boolean;
  setLeftCollapsed: (collapsed: boolean) => void;
  mobileMenuOpen: boolean;
  setMobileMenuOpen: (open: boolean) => void;
  isAuthenticated: boolean;
  userName?: string | null;
  userAvatar?: string | null;
  onLogout: () => void;
}

export function SidebarContent({
  isZh,
  locale,
  leftCollapsed,
  setLeftCollapsed,
  mobileMenuOpen,
  setMobileMenuOpen,
  isAuthenticated,
  userName,
  userAvatar,
  onLogout,
}: SidebarContentProps) {
  const { sessions, currentSession, loading: sessionsLoading } = useSessions({
    enabled: isAuthenticated,
    loadMessages: false,
  });
  const { knowledgeBases } = useKnowledgeBases({ limit: 5, sortBy: "updated", enabled: isAuthenticated });

  const primaryWorkspaceItems = useMemo(
    () => workspaceItems.filter((item) => PRIMARY_WORKSPACE_ITEMS.includes(item.to)),
    [],
  );
  const overflowWorkspaceItems = useMemo(
    () => workspaceItems.filter((item) => !PRIMARY_WORKSPACE_ITEMS.includes(item.to)),
    [],
  );

  const handleNavigate = () => setMobileMenuOpen(false);

  return (
    <div className="z-20 flex h-full flex-col border-r-2 border-border/70 bg-gradient-to-b from-muted/40 to-background shadow-2xl">
      {/* Header: Logo + New Thread + Collapse */}
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
            <Link
              to="/dashboard"
              onClick={handleNavigate}
              className="group flex min-w-0 items-center gap-3 text-left transition-colors"
            >
              <Logo className="min-w-0 gap-2.5" markSize={34} textClassName="text-[1.65rem] leading-none" />
              <div className="ml-auto flex items-center gap-1.5">
                <span className="relative flex h-2.5 w-2.5">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary/40" />
                  <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-primary/70" />
                </span>
              </div>
            </Link>
          </div>
        )}

        <div className={clsx("mt-5 flex items-center", leftCollapsed ? "justify-center" : "justify-between gap-3")}>
          <Link
            to="/chat?new=1"
            onClick={handleNavigate}
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
          </Link>
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

      {/* Workspace Nav */}
      <div className={clsx("shrink-0 border-b border-border/60", leftCollapsed ? "px-2 py-3" : "px-5 py-4")}>
        {!leftCollapsed ? (
          <div className="mb-3 text-[10px] font-semibold text-muted-foreground/80">
            {isZh ? "工作区" : "Workspace"}
          </div>
        ) : null}
        <div className={clsx(leftCollapsed ? "space-y-1" : "space-y-0.5")}>
          {primaryWorkspaceItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={handleNavigate}
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
        {overflowWorkspaceItems.length > 0 ? (
          <div className={clsx("mt-3", leftCollapsed ? "" : "rounded-2xl border border-border/60 bg-background/65 shadow-sm")}>
            {!leftCollapsed ? (
              <div className="px-3 pb-2 pt-2 text-[9px] font-bold uppercase tracking-[0.22em] text-muted-foreground/75">
                {isZh ? "更多工作区" : "More"}
              </div>
            ) : null}
            <ScrollArea className={clsx(leftCollapsed ? "h-[8.5rem]" : "h-[8.75rem]")}>
              <div className={clsx("space-y-0.5", leftCollapsed ? "px-0" : "px-2 pb-2")}>
                {overflowWorkspaceItems.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    onClick={handleNavigate}
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
            </ScrollArea>
          </div>
        ) : null}
      </div>

      {/* Session List + Knowledge Bases */}
      <div className={clsx("min-h-0 flex-1 overflow-y-auto", leftCollapsed ? "px-2 py-3" : "px-5 py-4")}>
        {!leftCollapsed ? (
          <section>
            <div className="mb-2 flex items-center justify-between px-2">
              <span className="flex items-center gap-1.5 text-[9px] font-bold uppercase tracking-[0.28em] text-muted-foreground">
                <MessagesSquare className="h-3 w-3" />
                {isZh ? "最近对话" : "Recent Threads"}
              </span>
              <Link
                to="/dashboard"
                onClick={handleNavigate}
                className="text-[10px] text-muted-foreground/70 transition-colors hover:text-primary"
              >
                {isZh ? "进入" : "Open"}
              </Link>
            </div>
            <SessionList
              sessions={sessions}
              currentSession={currentSession}
              loading={sessionsLoading}
              isZh={isZh}
              locale={locale}
              leftCollapsed={leftCollapsed}
              onNavigate={handleNavigate}
            />
          </section>
        ) : (
          <SessionList
            sessions={sessions}
            currentSession={currentSession}
            loading={sessionsLoading}
            isZh={isZh}
            locale={locale}
            leftCollapsed={leftCollapsed}
            onNavigate={handleNavigate}
          />
        )}

        {!leftCollapsed && knowledgeBases.length > 0 && (
          <section className="mt-6">
            <div className="mb-2 flex items-center justify-between px-2">
              <span className="flex items-center gap-1.5 text-[9px] font-bold uppercase tracking-[0.28em] text-muted-foreground">
                <BookOpen className="h-3 w-3" />
                {isZh ? "资料馆藏" : "Collections"}
              </span>
              <Link
                to="/knowledge-bases"
                onClick={handleNavigate}
                className="text-[10px] text-muted-foreground/70 transition-colors hover:text-primary"
              >
                {isZh ? "进入" : "Open"}
              </Link>
            </div>
            <div className="space-y-0.5">
              {knowledgeBases.slice(0, 3).map((kb) => {
                const display = getKnowledgeBaseDisplayMetadata(kb);
                return (
                  <Link
                    key={kb.id}
                    to={`/knowledge-bases/${kb.id}`}
                    onClick={handleNavigate}
                    title={display.displayName}
                    className="group flex w-full items-start gap-2 border-l border-transparent px-0 py-2 pl-3 text-left transition-colors hover:border-border/80"
                  >
                    <BookOpen className="mt-0.5 h-3.5 w-3.5 shrink-0 text-foreground/55 transition-colors group-hover:text-foreground/70" />
                    <div className="min-w-0">
                      <div className="truncate text-[11.5px] font-medium text-foreground">
                        {display.displayName}
                      </div>
                      <div className="mt-1 text-[10px] text-muted-foreground">
                        {kb.paperCount}{isZh ? " 篇论文" : " papers"}
                      </div>
                    </div>
                  </Link>
                );
              })}
            </div>
          </section>
        )}
      </div>

      {/* User Profile Footer */}
      <div className={clsx("shrink-0 border-t border-border/60 bg-primary/[0.01]", leftCollapsed ? "px-2 pb-3 pt-3" : "px-3 pb-4 pt-3")}>
        <UserProfile
          userName={userName}
          userAvatar={userAvatar}
          isZh={isZh}
          leftCollapsed={leftCollapsed}
          onLogout={onLogout}
          onNavigate={handleNavigate}
        />
      </div>
    </div>
  );
}
