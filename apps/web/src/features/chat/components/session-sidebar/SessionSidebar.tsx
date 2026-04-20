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
      <div className="w-12 border-r border-zinc-200 flex flex-col h-full bg-zinc-50/70 items-center py-3 gap-3">
        <button
          onClick={() => setCollapsed(false)}
          className="w-8 h-8 flex items-center justify-center hover:bg-zinc-100 transition-colors rounded-sm text-zinc-500 hover:text-primary"
          title={isZh ? '展开侧边栏' : 'Expand sidebar'}
        >
          <PanelLeftOpen className="w-4 h-4" />
        </button>
        <button
          onClick={onCreateSession}
          data-testid="session-create-button"
          className="w-8 h-8 border border-zinc-300 hover:border-primary hover:text-primary transition-colors flex items-center justify-center"
          title={isZh ? '新建对话' : 'New chat'}
        >
          <Plus className="w-4 h-4" />
        </button>
        <div className="w-px h-4 bg-zinc-200" />
        {sessions.slice(0, 8).map((s) => (
          <button
            key={s.id}
            onClick={() => onSwitchSession(s.id)}
            title={s.title}
            className={clsx(
              'w-8 h-8 flex items-center justify-center transition-colors rounded-sm',
              currentSessionId === s.id
                ? 'bg-primary/10 text-primary'
                : 'text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700'
            )}
          >
            <MessageSquare className="w-3.5 h-3.5" />
          </button>
        ))}
      </div>
    );
  }

  return (
    <div className="w-[252px] border-r border-zinc-200 flex flex-col h-full bg-zinc-50/70">
      <div className="px-3 py-3 border-b border-zinc-200 flex items-center justify-between bg-zinc-50/90">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setCollapsed(true)}
            className="p-1 hover:bg-zinc-100 transition-colors rounded-sm text-zinc-400 hover:text-zinc-600"
            title={isZh ? '收起侧边栏' : 'Collapse sidebar'}
          >
            <PanelLeftClose className="w-3.5 h-3.5" />
          </button>
          <div>
            <h2 className="font-serif text-sm font-bold tracking-tight leading-none">{labels.terminal}</h2>
            <p className="text-[9px] tracking-[0.14em] uppercase text-zinc-400 mt-0.5">{labels.sessions}</p>
          </div>
        </div>
        <button
          onClick={onCreateSession}
          data-testid="session-create-button"
          className="w-7 h-7 border border-zinc-300 hover:border-primary hover:text-primary transition-colors flex items-center justify-center rounded-sm"
          title={isZh ? '新建对话' : 'New chat'}
        >
          <Plus className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="px-3 py-2 border-b border-zinc-100">
        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-0 top-1/2 -translate-y-1/2 text-zinc-400" />
          <input
            type="text"
            placeholder={labels.search}
            value={searchValue}
            onChange={(event) => onSearchChange(event.target.value)}
            aria-label={labels.search}
            data-testid="session-search-input"
            className="w-full bg-transparent border-b border-zinc-200 pl-5 pr-1 py-1.5 text-xs placeholder:text-zinc-400 focus:outline-none focus:border-primary"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto py-1">
        {loading && sessions.length === 0 ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-5 h-5 animate-spin text-zinc-400" />
          </div>
        ) : sessions.length === 0 ? (
          <div className="text-center py-10 px-4 text-zinc-400 text-xs" data-testid="session-empty-state">
            <MessageSquare className="w-6 h-6 mx-auto mb-2 opacity-40" />
            {searchValue.trim() ? labels.noSearchResults : labels.newChat}
          </div>
        ) : (
          <div>
            {grouped.map(({ group, items }) => (
              <div key={group}>
                <div className="px-3 py-1.5 text-[9px] font-bold tracking-[0.16em] uppercase text-zinc-400">
                  {groupLabels[group]}
                </div>
                {items.map((session) => (
                  <div
                    key={session.id}
                    onClick={() => onSwitchSession(session.id)}
                    data-testid="session-item"
                    className={clsx(
                      'w-full text-left px-3 py-2 transition-colors group flex items-center gap-2 cursor-pointer',
                      currentSessionId === session.id
                        ? 'bg-primary/8 border-l-2 border-l-primary'
                        : 'hover:bg-zinc-100 border-l-2 border-l-transparent'
                    )}
                  >
                    <MessageSquare className={clsx(
                      'w-3.5 h-3.5 flex-shrink-0',
                      currentSessionId === session.id ? 'text-primary' : 'text-zinc-400'
                    )} />
                    <div className="flex-1 min-w-0">
                      <div className={clsx(
                        'text-xs font-medium truncate leading-snug',
                        currentSessionId === session.id ? 'text-primary' : 'text-zinc-700'
                      )}>
                        {session.title}
                      </div>
                      <div className="text-[10px] text-zinc-400 mt-0.5">
                        {session.messageCount} {labels.messageSuffix}
                      </div>
                    </div>
                    <button
                      onClick={(event) => onDeleteSession(session.id, event)}
                      data-testid={`session-delete-${session.id}`}
                      className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-50 transition-all flex-shrink-0 rounded-sm"
                    >
                      <Trash2 className="w-3 h-3 text-zinc-400 hover:text-destructive" />
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
