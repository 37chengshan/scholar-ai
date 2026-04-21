import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Chat } from './Chat';

vi.mock('@/features/chat/workspace/ChatWorkspaceV2', () => ({
  ChatWorkspaceV2: () => <div data-testid="chat-workspace-v2">chat-workspace-v2</div>,
}));

describe('Chat page shell', () => {
  it('renders the single production chat workspace path', () => {
    render(<Chat />);
    expect(screen.getByTestId('chat-workspace-v2')).toBeInTheDocument();
  });
});
