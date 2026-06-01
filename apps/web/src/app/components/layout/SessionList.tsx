import { useMemo } from "react";
import { Link, useLocation } from "react-router";
import { MessagesSquare } from "lucide-react";
import { clsx } from "clsx";
import type { ChatSession } from "@/app/hooks/useSessions";
import { applyScopeMetadataToSearchParams } from "@/features/chat/hooks/chatScopeQuery";

type DateGroup = { label: string; sessions: ChatSession[] };

function startOfDay(d: Date) {
  const c = new Date(d);
  c.setHours(0, 0, 0, 0);
  return c;
}

export function groupSessionsByDate(sessions: ChatSession[], isZh: boolean): DateGroup[] {
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

function buildSessionHref(session: ChatSession): string {
  const params = applyScopeMetadataToSearchParams(
    new URLSearchParams(),
    (session.metadata as Record<string, unknown> | null) ?? undefined,
  );
  params.set("session", session.id);
  return `/chat?${params.toString()}`;
}

interface SessionListProps {
  sessions: ChatSession[];
  currentSession: ChatSession | null;
  loading: boolean;
  isZh: boolean;
  locale: string;
  leftCollapsed: boolean;
  onNavigate: () => void;
}

export function SessionList({
  sessions,
  currentSession,
  loading,
  isZh,
  locale,
  leftCollapsed,
  onNavigate,
}: SessionListProps) {
  const location = useLocation();
  const currentQuery = new URLSearchParams(location.search);
  const activeSessionId = currentQuery.get("session");

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

  if (loading) {
    return (
      <div className={clsx("text-xs text-muted-foreground", leftCollapsed ? "px-0 py-3 text-center" : "px-2 py-3")}>
        {isZh ? "载入中…" : "Loading…"}
      </div>
    );
  }

  if (dateGroups.length === 0) {
    return (
      <div className={clsx(
        "text-xs leading-5 text-muted-foreground",
        leftCollapsed ? "px-0 py-2 text-center" : "border-l border-border/70 px-3 py-2",
      )}>
        {leftCollapsed ? "…" : isZh ? "还没有历史对话，点击上方按钮开始。" : "No threads yet. Start one from the primary action above."}
      </div>
    );
  }

  return (
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
                <Link
                  key={session.id}
                  to={buildSessionHref(session)}
                  onClick={onNavigate}
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
                </Link>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
