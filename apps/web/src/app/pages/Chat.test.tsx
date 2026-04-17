import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Chat } from './Chat';

vi.mock('@/features/chat/components/ChatWorkspace', () => ({
  ChatWorkspace: () => <div data-testid="chat-workspace">chat-workspace</div>,
}));

describe('Chat page shell', () => {
  it('renders chat workspace container', () => {
    render(<Chat />);
    expect(screen.getByTestId('chat-workspace')).toBeInTheDocument();
  });
});
