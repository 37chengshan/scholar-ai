import type { NavigateFunction } from 'react-router';
import type { ChatHandoffNavigationState, ChatHandoffState } from '@/features/workflow/commandCenter';

export interface ChatScopeParams {
  paperId?: string;
  kbId?: string;
  paperIds?: string[];
}

export interface PersistedChatHandoff {
  scope: ChatScopeParams;
  handoff: ChatHandoffState;
  savedAt: string;
}

const CHAT_HANDOFF_STORAGE_KEY = 'scholarai_chat_handoff_v1';

export function buildChatHref(scope: ChatScopeParams): string {
  const params = new URLSearchParams();

  if (scope.paperId) {
    params.set('paperId', scope.paperId);
  }
  if (scope.kbId) {
    params.set('kbId', scope.kbId);
  }
  if (scope.paperIds && scope.paperIds.length > 0) {
    params.set('paper_ids', scope.paperIds.join(','));
  }

  const query = params.toString();
  return query ? `/chat?${query}` : '/chat';
}

export function buildFreshChatHref(scope: ChatScopeParams): string {
  const href = buildChatHref(scope);
  const [pathname, search = ''] = href.split('?');
  const params = new URLSearchParams(search);
  params.set('new', '1');
  params.delete('session');
  const query = params.toString();
  return query ? `${pathname}?${query}` : pathname;
}

export function shouldPreserveComposerDraftForHandoff(search: string): boolean {
  const params = new URLSearchParams(search);
  return params.get('handoff') === '1';
}

export function buildHandoffChatHref(scope: ChatScopeParams): string {
  const href = buildChatHref(scope);
  const [pathname, search = ''] = href.split('?');
  const params = new URLSearchParams(search);
  params.set('handoff', '1');
  params.set('new', '1');
  params.delete('session');
  const query = params.toString();
  return query ? `${pathname}?${query}` : pathname;
}

function canUseSessionStorage(): boolean {
  return typeof window !== 'undefined' && typeof window.sessionStorage !== 'undefined';
}

export function persistChatHandoff(scope: ChatScopeParams, handoff: ChatHandoffState): void {
  if (!canUseSessionStorage()) {
    return;
  }

  const payload: PersistedChatHandoff = {
    scope,
    handoff,
    savedAt: new Date().toISOString(),
  };

  window.sessionStorage.setItem(CHAT_HANDOFF_STORAGE_KEY, JSON.stringify(payload));
}

export function readPersistedChatHandoff(): PersistedChatHandoff | null {
  if (!canUseSessionStorage()) {
    return null;
  }

  const raw = window.sessionStorage.getItem(CHAT_HANDOFF_STORAGE_KEY);
  if (!raw) {
    return null;
  }

  try {
    const parsed = JSON.parse(raw) as PersistedChatHandoff;
    if (!parsed || !parsed.handoff || !parsed.scope) {
      return null;
    }
    return parsed;
  } catch {
    window.sessionStorage.removeItem(CHAT_HANDOFF_STORAGE_KEY);
    return null;
  }
}

export function matchesPersistedChatHandoff(search: string, persisted: PersistedChatHandoff | null): persisted is PersistedChatHandoff {
  if (!persisted) {
    return false;
  }

  const params = new URLSearchParams(search);
  if (params.get('handoff') !== '1') {
    return false;
  }

  const paperId = params.get('paperId') || undefined;
  const kbId = params.get('kbId') || undefined;
  const paperIds = (params.get('paper_ids') || '')
    .split(',')
    .map((id) => id.trim())
    .filter(Boolean);
  const persistedPaperIds = persisted.scope.paperIds || [];

  return (
    paperId === persisted.scope.paperId
    && kbId === persisted.scope.kbId
    && paperIds.join(',') === persistedPaperIds.join(',')
  );
}

export function navigateToChatWithHandoff(
  navigate: NavigateFunction,
  scope: ChatScopeParams,
  handoff: ChatHandoffState,
) {
  persistChatHandoff(scope, handoff);

  navigate(buildHandoffChatHref(scope), {
    state: {
      handoff,
    } satisfies ChatHandoffNavigationState,
  });
}
