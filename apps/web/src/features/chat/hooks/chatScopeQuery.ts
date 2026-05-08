import type { WorkspaceScope } from '@/features/chat/state/chatWorkspaceStore';
import type { SessionScopeMetadata } from '@/services/sessionsApi';
import type { KnowledgeBase } from '@/services/kbApi';

export function buildSessionScopeMetadata(scope: WorkspaceScope): SessionScopeMetadata {
  if (scope.type === 'single_paper' && scope.id) {
    return {
      scopeType: 'single_paper',
      paperId: scope.id,
      title: scope.title,
    };
  }

  if (scope.type === 'full_kb' && scope.id) {
    return {
      scopeType: 'full_kb',
      kbId: scope.id,
      title: scope.title,
    };
  }

  if (scope.type === 'compare' && scope.id) {
    const paperIds = scope.id
      .split(',')
      .map((id) => id.trim())
      .filter(Boolean);
    if (paperIds.length > 0) {
      return {
        scopeType: 'compare',
        paperIds,
        title: scope.title,
      };
    }
  }

  return {};
}

export function enrichKnowledgeBaseScopeMetadata(
  metadata: SessionScopeMetadata,
  knowledgeBase: Pick<KnowledgeBase, 'updatedAt' | 'paperCount' | 'chunkCount'>,
): SessionScopeMetadata {
  if (metadata.scopeType !== 'full_kb') {
    return metadata;
  }

  return {
    ...metadata,
    kbUpdatedAt: knowledgeBase.updatedAt,
    kbPaperCount: knowledgeBase.paperCount,
    kbChunkCount: knowledgeBase.chunkCount,
  };
}

export function applyScopeMetadataToSearchParams(
  searchParams: URLSearchParams,
  metadata?: SessionScopeMetadata | null,
): URLSearchParams {
  const next = new URLSearchParams(searchParams);
  next.delete('paperId');
  next.delete('kbId');
  next.delete('paper_ids');

  if (!metadata?.scopeType) {
    return next;
  }

  if (metadata.scopeType === 'single_paper' && metadata.paperId) {
    next.set('paperId', metadata.paperId);
    return next;
  }

  if (metadata.scopeType === 'full_kb' && metadata.kbId) {
    next.set('kbId', metadata.kbId);
    return next;
  }

  if (metadata.scopeType === 'compare' && Array.isArray(metadata.paperIds) && metadata.paperIds.length > 0) {
    next.set('paper_ids', metadata.paperIds.join(','));
  }

  return next;
}

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
      type: 'compare',
      id: comparePaperIds.join(','),
      title: `Comparison set (${comparePaperIds.length})`,
    };
  }

  return {
    type: null,
    id: null,
  };
}
