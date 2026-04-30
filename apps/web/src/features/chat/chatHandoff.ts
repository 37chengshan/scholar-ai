import type { NavigateFunction } from 'react-router';
import type { ChatHandoffNavigationState, ChatHandoffState } from '@/features/workflow/commandCenter';

export interface ChatScopeParams {
  paperId?: string;
  kbId?: string;
  paperIds?: string[];
}

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

export function navigateToChatWithHandoff(
  navigate: NavigateFunction,
  scope: ChatScopeParams,
  handoff: ChatHandoffState,
) {
  navigate(buildChatHref(scope), {
    state: {
      handoff,
    } satisfies ChatHandoffNavigationState,
  });
}
