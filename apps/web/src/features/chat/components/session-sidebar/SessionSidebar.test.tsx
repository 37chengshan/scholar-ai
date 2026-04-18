import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { SessionSidebar } from './SessionSidebar';

describe('SessionSidebar', () => {
  it('renders sessions and triggers callbacks', async () => {
    const user = userEvent.setup();
    const onCreateSession = vi.fn();
    const onSwitchSession = vi.fn();
    const onDeleteSession = vi.fn();

    render(
      <SessionSidebar
        sessions={[
          {
            id: 'session-1',
            title: 'Alpha',
            status: 'active',
            messageCount: 2,
            createdAt: '2026-01-01T00:00:00Z',
          },
        ]}
        currentSessionId={'session-1'}
        loading={false}
        labels={{
          terminal: 'Terminal',
          sessions: 'Sessions',
          search: 'Search...',
          history: 'History',
          newChat: 'New Chat',
          messageSuffix: 'messages',
        }}
        onCreateSession={onCreateSession}
        onSwitchSession={onSwitchSession}
        onDeleteSession={onDeleteSession}
      />
    );

    const buttons = screen.getAllByRole('button');
    await user.click(buttons[0]);
    expect(onCreateSession).toHaveBeenCalledTimes(1);

    await user.click(screen.getByText('Alpha'));
    expect(onSwitchSession).toHaveBeenCalledWith('session-1');

    await user.click(buttons[1]);
    expect(onDeleteSession).toHaveBeenCalledTimes(1);
  });
});
