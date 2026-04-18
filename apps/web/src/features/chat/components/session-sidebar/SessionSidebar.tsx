import { Plus, Search, Loader2, MessageSquare, Trash2 } from 'lucide-react';
import { clsx } from 'clsx';
import type { ChatSession } from '@/app/hooks/useSessions';

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
  onSearchChange,
  onCreateSession,
  onSwitchSession,
  onDeleteSession,
}: SessionSidebarProps) {
  return (
    <div className="w-[252px] border-r border-zinc-200 flex flex-col h-full bg-zinc-50/70">
      <div className="px-4 py-3 border-b border-zinc-200 flex items-center justify-between bg-zinc-50/90">
        <div>
          <h2 className="font-serif text-base font-bold tracking-tight">{labels.terminal}</h2>
          <p className="text-[10px] tracking-[0.14em] uppercase text-zinc-500">{labels.sessions}</p>
        </div>
        <button
          onClick={onCreateSession}
          data-testid="session-create-button"
          className="w-8 h-8 border border-zinc-300 hover:border-primary hover:text-primary transition-colors flex items-center justify-center"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>

      <div className="px-3 py-2 border-b border-zinc-200">
        <div className="relative">
          <Search className="w-4 h-4 absolute left-0 top-1/2 -translate-y-1/2 text-zinc-400" />
          <input
            type="text"
            placeholder={labels.search}
            value={searchValue}
            onChange={(event) => onSearchChange(event.target.value)}
            aria-label={labels.search}
            data-testid="session-search-input"
            className="w-full bg-transparent border-b border-zinc-200 pl-6 pr-1 py-1.5 text-sm placeholder:text-zinc-400 focus:outline-none focus:border-primary focus-visible:ring-2 focus-visible:ring-primary/40"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto py-2 px-2">
        <div className="text-[10px] font-bold tracking-[0.14em] uppercase text-zinc-500 mb-2 px-2">
          {labels.history}
        </div>

        {loading && sessions.length === 0 ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
          </div>
        ) : sessions.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground text-sm" data-testid="session-empty-state">
            {searchValue.trim() ? labels.noSearchResults : labels.newChat}
          </div>
        ) : (
          <div className="space-y-1">
            {sessions.map((session) => (
              <div
                key={session.id}
                onClick={() => onSwitchSession(session.id)}
                data-testid="session-item"
                className={clsx(
                  'w-full text-left px-3 py-2.5 transition-colors group flex items-start gap-2 cursor-pointer border-b border-zinc-100',
                  currentSessionId === session.id
                    ? 'bg-zinc-100/80 border-l-2 border-l-primary'
                    : 'hover:bg-zinc-100/50 border-l-2 border-l-transparent'
                )}
              >
                <MessageSquare className="w-4 h-4 mt-0.5 text-zinc-500 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <div
                    className={clsx(
                      'text-sm font-medium truncate',
                      currentSessionId === session.id ? 'text-primary' : 'text-foreground'
                    )}
                  >
                    {session.title}
                  </div>
                  <div className="text-xs text-muted-foreground mt-0.5">
                    {session.messageCount} {labels.messageSuffix}
                  </div>
                </div>
                <button
                  onClick={(event) => onDeleteSession(session.id, event)}
                  data-testid={`session-delete-${session.id}`}
                  className="opacity-0 group-hover:opacity-100 p-1 hover:bg-destructive/10 transition-opacity flex-shrink-0"
                >
                  <Trash2 className="w-3.5 h-3.5 text-muted-foreground hover:text-destructive" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
