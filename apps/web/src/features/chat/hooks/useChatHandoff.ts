import { useEffect, useMemo, useRef } from 'react';
import { useLocation } from 'react-router';
import type { ChatHandoffNavigationState, ChatHandoffState } from '@/features/workflow/commandCenter';

function describeOrigin(origin: ChatHandoffState['origin'], isZh: boolean): string {
  if (isZh) {
    switch (origin) {
      case 'search':
        return 'Search';
      case 'kb':
        return 'Knowledge Base';
      case 'read':
        return 'Read';
      case 'notes':
        return 'Notes';
      case 'compare':
        return 'Compare';
      case 'review':
        return 'Review';
      default:
        return 'Dashboard';
    }
  }

  switch (origin) {
    case 'kb':
      return 'Knowledge Base';
    case 'read':
      return 'Read';
    case 'notes':
      return 'Notes';
    case 'compare':
      return 'Compare';
    case 'review':
      return 'Review';
    case 'search':
      return 'Search';
    default:
      return 'Dashboard';
  }
}

export function useChatHandoff(params: {
  isZh: boolean;
  setComposerDraft: (draft: string) => void;
}) {
  const { isZh, setComposerDraft } = params;
  const location = useLocation();
  const consumedSignatureRef = useRef<string | null>(null);
  const handoff = ((location.state as ChatHandoffNavigationState | null)?.handoff ?? null);

  const handoffSignature = useMemo(() => {
    if (!handoff) {
      return null;
    }
    return JSON.stringify(handoff);
  }, [handoff]);

  useEffect(() => {
    if (!handoff || !handoffSignature || consumedSignatureRef.current === handoffSignature) {
      return;
    }

    consumedSignatureRef.current = handoffSignature;
    if (handoff.promptDraft) {
      setComposerDraft(handoff.promptDraft);
    }
  }, [handoff, handoffSignature, setComposerDraft]);

  if (!handoff) {
    return null;
  }

  return {
    originLabel: describeOrigin(handoff.origin, isZh),
    promptDraft: handoff.promptDraft,
    evidenceCount: handoff.evidence?.length || 0,
    returnTo: handoff.returnTo || null,
  };
}
