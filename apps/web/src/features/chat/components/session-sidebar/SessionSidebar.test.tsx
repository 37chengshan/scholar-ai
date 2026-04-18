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
    const onSearchChange = vi.fn();

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
          noSearchResults: 'No matching sessions',
          messageSuffix: 'messages',
        }}
        searchValue=""
        onSearchChange={onSearchChange}
        onCreateSession={onCreateSession}
        onSwitchSession={onSwitchSession}
        onDeleteSession={onDeleteSession}
      />
    );

    await user.click(screen.getByTestId('session-create-button'));
    expect(onCreateSession).toHaveBeenCalledTimes(1);

    await user.click(screen.getByText('Alpha'));
    expect(onSwitchSession).toHaveBeenCalledWith('session-1');

    await user.click(screen.getByTestId('session-delete-session-1'));
    expect(onDeleteSession).toHaveBeenCalledTimes(1);

    await user.type(screen.getByTestId('session-search-input'), 'alp');
    expect(onSearchChange).toHaveBeenCalled();
  });

  it('shows search empty state when no session matches', () => {
    render(
      <SessionSidebar
        sessions={[]}
        currentSessionId={null}
        loading={false}
        labels={{
          terminal: 'Terminal',
          sessions: 'Sessions',
          search: 'Search...',
          history: 'History',
          newChat: 'New Chat',
          noSearchResults: 'No matching sessions',
          messageSuffix: 'messages',
        }}
        searchValue="zz-not-found"
        onSearchChange={vi.fn()}
        onCreateSession={vi.fn()}
        onSwitchSession={vi.fn()}
        onDeleteSession={vi.fn()}
      />
    );

    expect(screen.getByTestId('session-empty-state')).toHaveTextContent('No matching sessions');
  });
});
