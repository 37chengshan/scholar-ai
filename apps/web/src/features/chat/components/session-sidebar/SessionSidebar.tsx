import { Plus, Search, Loader2, MessageSquare, Trash2, PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import { clsx } from 'clsx';
import { useState } from 'react';
import type { ChatSession } from '@/app/hooks/useSessions';

// ---- Time grouping helpers ----
type TimeGroup = 'today' | 'yesterday' | 'thisWeek' | 'earlier';

function getTimeGroup(dateStr: string): TimeGroup {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = diffMs / (1000 * 60 * 60 * 24);
  if (diffDays < 1) return 'today';
  if (diffDays < 2) return 'yesterday';
  if (diffDays < 7) return 'thisWeek';
  return 'earlier';
}

function groupSessions(sessions: ChatSession[]): { group: TimeGroup; items: ChatSession[] }[] {
  const groups: Record<TimeGroup, ChatSession[]> = {
    today: [], yesterday: [], thisWeek: [], earlier: [],
  };
  for (const s of sessions) {
    const key = getTimeGroup(s.updatedAt || s.createdAt || new Date().toISOString());
    groups[key].push(s);
  }
  const order: TimeGroup[] = ['today', 'yesterday', 'thisWeek', 'earlier'];
  return order.filter(g => groups[g].length > 0).map(g => ({ group: g, items: groups[g] }));
}

const GROUP_LABELS_ZH: Record<TimeGroup, string> = {
  today: '今天', yesterday: '昨天', thisWeek: '本周', earlier: '更早',
};
const GROUP_LABELS_EN: Record<TimeGroup, string> = {
  today: 'Today', yesterday: 'Yesterday', thisWeek: 'This Week', earlier: 'Earlier',
};

interface SessionSidebarCopy {
  terminal: string;
  sessions: string;
  search: string;
  history: string;
  newChat: string;
  noSearchResults: string;
  messageSuffix: string;
}

interface SessionSidebarProps {
  sessions: ChatSession[];
  currentSessionId: string | null;
  loading: boolean;
  labels: SessionSidebarCopy;
  searchValue: string;
  isZh?: boolean;
  onSearchChange: (value: string) => void;
  onCreateSession: () => void;
  onSwitchSession: (sessionId: string) => void;
  onDeleteSession: (sessionId: string, event: React.MouseEvent) => void;
}

export function SessionSidebar({
  sessions,
  currentSessionId,
  loading,
  labels,
  searchValue,
  isZh = true,
  onSearchChange,
  onCreateSession,
  onSwitchSession,
  onDeleteSession,
}: SessionSidebarProps) {
  const [collapsed, setCollapsed] = useState(false);
  const groupLabels = isZh ? GROUP_LABELS_ZH : GROUP_LABELS_EN;
  const grouped = groupSessions(sessions);

  // Collapsed sidebar: icon-only rail
  if (collapsed) {
    return (
      <div className="w-12 border-r border-border/50 flex flex-col h-full bg-muted/20 items-center py-3 gap-2">
        <button
          onClick={() => setCollapsed(false)}
          className="w-8 h-8 flex items-center justify-center hover:bg-muted transition-colors rounded-sm text-muted-foreground hover:text-foreground"
          title={isZh ? '展开侧边栏' : 'Expand sidebar'}
        >
          <PanelLeftOpen className="w-4 h-4" />
        </button>
        <button
          onClick={onCreateSession}
          data-testid="session-create-button"
          className="w-8 h-8 hover:bg-primary/10 hover:text-primary transition-colors flex items-center justify-center rounded-sm text-muted-foreground"
          title={isZh ? '新建对话' : 'New chat'}
        >
          <Plus className="w-4 h-4" />
        </button>
        <div className="w-5 h-px bg-border my-1" />
        {sessions.slice(0, 8).map((s) => (
          <button
            key={s.id}
            onClick={() => onSwitchSession(s.id)}
            title={s.title}
            className={clsx(
              'w-8 h-8 flex items-center justify-center transition-colors rounded-sm',
              currentSessionId === s.id
                ? 'bg-primary/10 text-primary'
                : 'text-muted-foreground hover:bg-muted hover:text-foreground'
            )}
          >
            <MessageSquare className="w-3.5 h-3.5" />
          </button>
        ))}
      </div>
    );
  }

  return (
    <div className="w-[220px] border-r border-border/50 flex flex-col h-full bg-muted/20 transition-all duration-200 shrink-0">
      {/* Header */}
      <div className="border-b border-border/50 px-5 py-4 flex items-center justify-between bg-background/80 backdrop-blur-md sticky top-0 z-10">
        <h2 className="font-serif text-lg font-bold tracking-tight">Recents</h2>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setCollapsed(true)}
            className="p-1.5 hover:bg-muted transition-colors rounded-sm text-muted-foreground hover:text-foreground"
            title={isZh ? '收起侧边栏' : 'Collapse sidebar'}
          >
            <PanelLeftClose className="w-4 h-4" />
          </button>
          <button
            onClick={onCreateSession}
            data-testid="session-create-button"
            className="w-7 h-7 hover:bg-primary/10 hover:text-primary transition-colors flex items-center justify-center rounded-sm text-primary"
            title={isZh ? '新建对话' : 'New chat'}
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="px-4 py-4 border-b border-border/50">
        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder={labels.search}
            value={searchValue}
            onChange={(event) => onSearchChange(event.target.value)}
            aria-label={labels.search}
            data-testid="session-search-input"
            className="w-full bg-background border border-border/50 rounded-[4px] pl-8 pr-3 py-2 text-[11px] placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/30 transition-all font-sans shadow-sm"
          />
        </div>
      </div>

      {/* Session list */}
      <div className="flex-1 overflow-y-auto px-2 py-1">
        {loading && sessions.length === 0 ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
          </div>
        ) : sessions.length === 0 ? (
          <div className="text-center py-10 px-4 text-muted-foreground text-xs" data-testid="session-empty-state">
            <MessageSquare className="w-6 h-6 mx-auto mb-2 opacity-40" />
            {searchValue.trim() ? labels.noSearchResults : labels.newChat}
          </div>
        ) : (
          <div>
            {grouped.map(({ group, items }) => (
              <div key={group} className="mb-1">
                <div className="px-2 py-2 text-[10px] font-semibold tracking-[0.12em] uppercase text-muted-foreground">
                  {groupLabels[group]}
                </div>
                {items.map((session) => (
                  <div
                    key={session.id}
                    onClick={() => onSwitchSession(session.id)}
                    data-testid="session-item"
                    role="button"
                    tabIndex={0}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault();
                        onSwitchSession(session.id);
                      }
                    }}
                    className={clsx(
                      'w-full text-left px-3 py-2.5 transition-all group flex items-start gap-2.5 rounded-sm mb-0.5',
                      currentSessionId === session.id
                        ? 'bg-primary/8 text-foreground'
                        : 'hover:bg-muted/80 text-foreground/75'
                    )}
                  >
                    <div className="flex-1 min-w-0">
                      <div className={clsx(
                        'text-[13px] font-medium truncate leading-snug',
                        currentSessionId === session.id ? 'text-foreground' : 'text-foreground/80'
                      )}>
                        {session.title}
                      </div>
                      <div className="text-[11px] text-muted-foreground mt-0.5 truncate">
                        {session.messageCount} {labels.messageSuffix}
                      </div>
                    </div>
                    <button
                      onClick={(event) => onDeleteSession(session.id, event)}
                      data-testid={`session-delete-${session.id}`}
                      type="button"
                      className="opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 p-1 hover:bg-destructive/10 focus-visible:bg-destructive/10 transition-all flex-shrink-0 rounded-md mt-0.5"
                      aria-label={isZh ? '删除会话' : 'Delete session'}
                    >
                      <Trash2 className="w-3 h-3 text-muted-foreground hover:text-destructive" />
                    </button>
                  </div>
                ))}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
