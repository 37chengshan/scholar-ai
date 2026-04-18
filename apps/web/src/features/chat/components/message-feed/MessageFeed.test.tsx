import { createRef } from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { createInitialState } from '@/app/hooks/useChatStream';
import { MessageFeed } from './MessageFeed';

describe('MessageFeed', () => {
  it('renders empty state', () => {
    render(
      <MessageFeed
        localMessages={[]}
        streamState={createInitialState()}
        currentMessageId={''}
        thinkingSteps={[]}
        labels={{ noMessages: '开始新对话', sendFirst: '发送第一条消息', thinking: '思考中', stop: '停止' }}
        messagesEndRef={createRef<HTMLDivElement>()}
        onCitationClick={() => {}}
        onStop={() => {}}
        formatTime={() => '10:00'}
      />
    );

    expect(screen.getByText('开始新对话')).toBeInTheDocument();
  });

  it('calls stop on streaming message', async () => {
    const user = userEvent.setup();
    const onStop = vi.fn();

    render(
      <MessageFeed
        localMessages={[
          {
            id: 'placeholder-1',
            session_id: 's1',
            role: 'assistant',
            content: 'content',
            created_at: '2026-01-01T00:00:00Z',
            streamStatus: 'streaming',
            isThinkingExpanded: true,
          },
        ]}
        streamState={createInitialState()}
        currentMessageId={'placeholder-1'}
        thinkingSteps={[]}
        labels={{ noMessages: '开始新对话', sendFirst: '发送第一条消息', thinking: '思考中', stop: '停止' }}
        messagesEndRef={createRef<HTMLDivElement>()}
        onCitationClick={() => {}}
        onStop={onStop}
        formatTime={() => '10:00'}
      />
    );

    await user.click(screen.getByRole('button', { name: '停止' }));
    expect(onStop).toHaveBeenCalledTimes(1);
  });
});
