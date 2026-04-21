import { renderHook, act } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useChatSessionController } from './useChatSessionController';

const mocks = vi.hoisted(() => ({
  toastSuccess: vi.fn(),
  toastError: vi.fn(),
}));

vi.mock('sonner', () => ({
  toast: {
    success: mocks.toastSuccess,
    error: mocks.toastError,
  },
}));

describe('useChatSessionController', () => {
  beforeEach(() => {
    mocks.toastSuccess.mockReset();
    mocks.toastError.mockReset();
  });

  it('resets stream and runtime state when creating a new session succeeds', async () => {
    const disconnect = vi.fn();
    const createSession = vi.fn().mockResolvedValue({ id: 'session-1' });
    const resetForSessionSwitch = vi.fn();
    const resetRuntimeRun = vi.fn();
    const resetStreamingRun = vi.fn();
    const setSessionSearchQuery = vi.fn();
    const setSessionTokens = vi.fn();
    const setSessionCost = vi.fn();
    const sendLockRef = { current: true };

    const { result } = renderHook(() => useChatSessionController({
      isZh: true,
      sessionToDelete: null,
      createSession,
      switchSession: vi.fn(),
      deleteSession: vi.fn(),
      resetForSessionSwitch,
      resetRuntimeRun,
      resetStreamingRun,
      openDeleteConfirm: vi.fn(),
      closeDeleteConfirm: vi.fn(),
      setSessionSearchQuery,
      setSessionTokens,
      setSessionCost,
      sendLockRef,
      sseServiceRef: { current: { disconnect } as any },
    }));

    await act(async () => {
      await result.current.handleNewSession();
    });

    expect(disconnect).toHaveBeenCalledTimes(1);
    expect(sendLockRef.current).toBe(false);
    expect(createSession).toHaveBeenCalledWith('新对话');
    expect(setSessionSearchQuery).toHaveBeenCalledWith('');
    expect(resetForSessionSwitch).toHaveBeenCalledTimes(1);
    expect(resetRuntimeRun).toHaveBeenCalledTimes(1);
    expect(resetStreamingRun).toHaveBeenCalledTimes(1);
    expect(setSessionTokens).toHaveBeenCalledWith(0);
    expect(setSessionCost).toHaveBeenCalledWith(0);
  });

  it('opens delete confirm and closes it after successful deletion', async () => {
    const openDeleteConfirm = vi.fn();
    const closeDeleteConfirm = vi.fn();
    const stopPropagation = vi.fn();
    const deleteSession = vi.fn().mockResolvedValue(true);

    const { result } = renderHook(() => useChatSessionController({
      isZh: false,
      sessionToDelete: 'session-2',
      createSession: vi.fn(),
      switchSession: vi.fn(),
      deleteSession,
      resetForSessionSwitch: vi.fn(),
      resetRuntimeRun: vi.fn(),
      resetStreamingRun: vi.fn(),
      openDeleteConfirm,
      closeDeleteConfirm,
      setSessionSearchQuery: vi.fn(),
      setSessionTokens: vi.fn(),
      setSessionCost: vi.fn(),
      sendLockRef: { current: false },
      sseServiceRef: { current: null },
    }));

    act(() => {
      result.current.handleDeleteSession('session-2', { stopPropagation } as any);
    });

    expect(stopPropagation).toHaveBeenCalledTimes(1);
    expect(openDeleteConfirm).toHaveBeenCalledWith('session-2');

    await act(async () => {
      await result.current.confirmDeleteSession();
    });

    expect(deleteSession).toHaveBeenCalledWith('session-2');
    expect(mocks.toastSuccess).toHaveBeenCalledWith('Session deleted');
    expect(closeDeleteConfirm).toHaveBeenCalledTimes(1);
  });
});