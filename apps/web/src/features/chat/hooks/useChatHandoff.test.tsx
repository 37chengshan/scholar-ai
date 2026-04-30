import { renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useChatHandoff } from './useChatHandoff';

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
});
