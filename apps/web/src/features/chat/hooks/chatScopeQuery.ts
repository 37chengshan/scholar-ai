import type { WorkspaceScope } from '@/features/chat/state/chatWorkspaceStore';

export function parseScopeFromQuery(searchParams: URLSearchParams): WorkspaceScope {
  const paperId = searchParams.get('paperId');
  const kbId = searchParams.get('kbId');
  const comparePaperIds = (searchParams.get('paper_ids') || '')
    .split(',')
    .map((id) => id.trim())
    .filter(Boolean);

  if (paperId && kbId) {
    return {
      type: 'error',
      id: paperId,
      errorMessage: 'paperId and kbId cannot coexist',
    };
  }

  if (paperId) {
    return {
      type: 'single_paper',
      id: paperId,
    };
  }

  if (kbId) {
    return {
      type: 'full_kb',
      id: kbId,
    };
  }

  if (comparePaperIds.length > 0) {
    return {
      type: 'general',
      id: comparePaperIds.join(','),
      title: `Comparison set (${comparePaperIds.length})`,
    };
  }

  return {
    type: null,
    id: null,
  };
}
