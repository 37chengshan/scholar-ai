import { renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useChatHandoff } from './useChatHandoff';
import { persistChatHandoff } from '@/features/chat/chatHandoff';

let mockedLocation = {
  pathname: '/chat',
  search: '',
  state: null as unknown,
};

vi.mock('react-router', async () => {
  const actual = await vi.importActual<any>('react-router');
  return {
    ...actual,
    useLocation: () => mockedLocation,
  };
});

describe('useChatHandoff', () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    mockedLocation = {
      pathname: '/chat',
      search: '',
      state: null,
    };
  });

  it('hydrates the composer draft once from navigation handoff state', () => {
    const setComposerDraft = vi.fn();
    mockedLocation.state = {
      handoff: {
        origin: 'search',
        promptDraft: 'Compare the imported paper with prior work.',
        evidence: [{ paperId: 'paper-1', claim: 'Main contribution' }],
        returnTo: '/search?q=agent',
      },
    };

    const { result, rerender } = renderHook(() => useChatHandoff({ isZh: false, setComposerDraft }));

    expect(setComposerDraft).toHaveBeenCalledTimes(1);
    expect(setComposerDraft).toHaveBeenCalledWith('Compare the imported paper with prior work.');
    expect(result.current).toEqual({
      originLabel: 'Search',
      promptDraft: 'Compare the imported paper with prior work.',
      evidenceCount: 1,
      returnTo: '/search?q=agent',
    });

    rerender();
    expect(setComposerDraft).toHaveBeenCalledTimes(1);
  });

  it('returns null without mutating the composer when handoff state is absent', () => {
    const setComposerDraft = vi.fn();

    const { result } = renderHook(() => useChatHandoff({ isZh: true, setComposerDraft }));

    expect(result.current).toBeNull();
    expect(setComposerDraft).not.toHaveBeenCalled();
  });

  it('hydrates from persisted handoff when router state is absent but the chat URL is durable', () => {
    const setComposerDraft = vi.fn();
    mockedLocation.search = '?kbId=kb-1&handoff=1';
    persistChatHandoff(
      { kbId: 'kb-1' },
      {
        origin: 'review',
        promptDraft: 'Re-check the review paragraph against the cited evidence.',
        evidence: [{ paperId: 'paper-1' }],
        returnTo: '/knowledge-bases/kb-1?tab=review&runId=run-1',
      },
    );

    const { result } = renderHook(() => useChatHandoff({ isZh: false, setComposerDraft }));

    expect(setComposerDraft).toHaveBeenCalledWith('Re-check the review paragraph against the cited evidence.');
    expect(result.current).toEqual({
      originLabel: 'Review',
      promptDraft: 'Re-check the review paragraph against the cited evidence.',
      evidenceCount: 1,
      returnTo: '/knowledge-bases/kb-1?tab=review&runId=run-1',
    });
  });
});
