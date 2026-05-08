import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useSessions } from './useSessions';

const listSessionsMock = vi.fn();
const getSessionMessagesMock = vi.fn();

vi.mock('@/services/sessionsApi', () => ({
  listSessions: (...args: unknown[]) => listSessionsMock(...args),
  getSessionMessages: (...args: unknown[]) => getSessionMessagesMock(...args),
  createSession: vi.fn(),
  deleteSession: vi.fn(),
  updateSession: vi.fn(),
}));

describe('useSessions', () => {
  beforeEach(() => {
    listSessionsMock.mockReset();
    getSessionMessagesMock.mockReset();
  });

  it('skips message history loading when loadMessages is false', async () => {
    listSessionsMock.mockResolvedValue([
      {
        id: 'session-1',
        title: 'Recent chat',
        status: 'active',
        messageCount: 3,
        createdAt: '2026-05-07T10:00:00Z',
        updatedAt: '2026-05-07T10:05:00Z',
      },
    ]);

    const { result } = renderHook(() =>
      useSessions({ enabled: true, loadMessages: false }),
    );

    await waitFor(() => {
      expect(result.current.sessions).toHaveLength(1);
    });

    expect(result.current.currentSession?.id).toBe('session-1');
    expect(result.current.messages).toEqual([]);
    expect(getSessionMessagesMock).not.toHaveBeenCalled();
  });
});
