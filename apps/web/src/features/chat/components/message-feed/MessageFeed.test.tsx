import { createRef } from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { createInitialState } from '@/app/hooks/useChatStream';
import { MessageFeed } from './MessageFeed';
import type { ChatRenderMessage } from '@/features/chat/hooks/useChatMessagesViewModel';

function asRenderMessage(message: Partial<ChatRenderMessage>): ChatRenderMessage {
  return {
    id: message.id || 'm-1',
    session_id: message.session_id || 's1',
    role: message.role || 'assistant',
    content: message.content || '',
    created_at: message.created_at || '2026-01-01T00:00:00Z',
    streamStatus: message.streamStatus,
    isThinkingExpanded: message.isThinkingExpanded,
    toolTimeline: message.toolTimeline,
    citations: message.citations,
    tokensUsed: message.tokensUsed,
    cost: message.cost,
    displayContent: message.displayContent ?? message.content ?? '',
    displayReasoning: message.displayReasoning ?? '',
    displayToolTimeline: message.displayToolTimeline ?? [],
    displayCitations: message.displayCitations ?? [],
    isStreaming: message.isStreaming ?? message.streamStatus === 'streaming',
    isPlaceholder: message.isPlaceholder ?? false,
    reasoningBuffer: message.reasoningBuffer,
  };
}

describe('MessageFeed', () => {
  it('renders empty state', () => {
    render(
      <MessageFeed
        renderMessages={[]}
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
        renderMessages={[
          asRenderMessage({
            id: 'placeholder-1',
            session_id: 's1',
            role: 'assistant',
            content: 'content',
            displayContent: 'content',
            created_at: '2026-01-01T00:00:00Z',
            streamStatus: 'streaming',
            isStreaming: true,
            isPlaceholder: true,
            isThinkingExpanded: true,
          }),
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

  it('renders streaming assistant content directly without typing animation lag', () => {
    render(
      <MessageFeed
        renderMessages={[
          asRenderMessage({
            id: 'assistant-stream-1',
            session_id: 's1',
            role: 'assistant',
            content: '实时流式内容片段',
            displayContent: '实时流式内容片段',
            created_at: '2026-01-01T00:00:00Z',
            streamStatus: 'streaming',
            isStreaming: true,
          }),
        ]}
        streamState={createInitialState()}
        currentMessageId={'assistant-stream-1'}
        thinkingSteps={[]}
        labels={{ noMessages: '开始新对话', sendFirst: '发送第一条消息', thinking: '思考中', stop: '停止' }}
        messagesEndRef={createRef<HTMLDivElement>()}
        onCitationClick={() => {}}
        onStop={() => {}}
        formatTime={() => '10:00'}
      />
    );

    expect(screen.getByText('实时流式内容片段')).toBeInTheDocument();
  });

  it('shows stop button only for streaming assistant message', () => {
    render(
      <MessageFeed
        renderMessages={[
          asRenderMessage({
            id: 'user-stream-1',
            session_id: 's1',
            role: 'user',
            content: 'user content',
            displayContent: 'user content',
            created_at: '2026-01-01T00:00:00Z',
            streamStatus: 'streaming',
            isStreaming: true,
          }),
        ]}
        streamState={createInitialState()}
        currentMessageId={'user-stream-1'}
        thinkingSteps={[]}
        labels={{ noMessages: '开始新对话', sendFirst: '发送第一条消息', thinking: '思考中', stop: '停止' }}
        messagesEndRef={createRef<HTMLDivElement>()}
        onCitationClick={() => {}}
        onStop={() => {}}
        formatTime={() => '10:00'}
      />
    );

    expect(screen.queryByRole('button', { name: '停止' })).not.toBeInTheDocument();
  });

  it('does not fallback token/cost from global stream state to unrelated message', () => {
    const streamState = {
      ...createInitialState(),
      tokensUsed: 999,
      cost: 12.34,
      streamStatus: 'completed' as const,
    };

    render(
      <MessageFeed
        renderMessages={[
          asRenderMessage({
            id: 'assistant-1',
            session_id: 's1',
            role: 'assistant',
            content: '无 token 元数据',
            displayContent: '无 token 元数据',
            created_at: '2026-01-01T00:00:00Z',
          }),
          asRenderMessage({
            id: 'assistant-2',
            session_id: 's1',
            role: 'assistant',
            content: '有 token 元数据',
            displayContent: '有 token 元数据',
            created_at: '2026-01-01T00:01:00Z',
            tokensUsed: 128,
            cost: 0.2468,
          }),
        ]}
        streamState={streamState}
        currentMessageId={''}
        thinkingSteps={[]}
        labels={{ noMessages: '开始新对话', sendFirst: '发送第一条消息', thinking: '思考中', stop: '停止' }}
        messagesEndRef={createRef<HTMLDivElement>()}
        onCitationClick={() => {}}
        onStop={() => {}}
        formatTime={() => '10:00'}
      />
    );

    expect(screen.getByText('无 token 元数据')).toBeInTheDocument();
    expect(screen.getByText('有 token 元数据')).toBeInTheDocument();
    expect(screen.getByText(/Token:\s*128/)).toBeInTheDocument();
    expect(screen.queryByText(/Token:\s*999/)).not.toBeInTheDocument();
  });

  it('shows compact streaming meta tags and defers tool panel details until stream ends', () => {
    const streamState = {
      ...createInitialState(),
      streamStatus: 'streaming' as const,
      reasoningBuffer: '正在检索并推理',
      toolTimeline: [
        {
          id: 'tool-1',
          tool: 'search_docs',
          label: '检索文档',
          status: 'running' as const,
          startedAt: Date.now(),
          summary: '检索文档中',
        },
      ],
    };

    render(
      <MessageFeed
        renderMessages={[
          asRenderMessage({
            id: 'assistant-stream-meta',
            session_id: 's1',
            role: 'assistant',
            content: '流式正文',
            displayContent: '流式正文',
            created_at: '2026-01-01T00:00:00Z',
            isStreaming: true,
            displayReasoning: '',
            displayToolTimeline: [],
          }),
        ]}
        streamState={streamState}
        currentMessageId={'assistant-stream-meta'}
        thinkingSteps={[{ type: 'thinking', content: '正在思考中' }]}
        labels={{ noMessages: '开始新对话', sendFirst: '发送第一条消息', thinking: '思考中', stop: '停止' }}
        messagesEndRef={createRef<HTMLDivElement>()}
        onCitationClick={() => {}}
        onStop={() => {}}
        formatTime={() => '10:00'}
      />
    );

    expect(screen.getByText('思考中')).toBeInTheDocument();
    expect(screen.getByText('Tools')).toBeInTheDocument();
    expect(screen.queryByText('search_docs')).not.toBeInTheDocument();
  });

  it('does not leak active streaming meta tags into historical assistant messages', () => {
    const streamState = {
      ...createInitialState(),
      streamStatus: 'streaming' as const,
      reasoningBuffer: 'active reasoning',
      toolTimeline: [
        {
          id: 'tool-1',
          tool: 'search_docs',
          label: 'Search Docs',
          status: 'running' as const,
          startedAt: Date.now(),
          summary: 'fetching',
        },
      ],
    };

    render(
      <MessageFeed
        renderMessages={[
          asRenderMessage({
            id: 'assistant-historical',
            session_id: 's1',
            role: 'assistant',
            content: '历史消息',
            displayContent: '历史消息',
            streamStatus: 'completed',
            isStreaming: false,
          }),
          asRenderMessage({
            id: 'assistant-stream-active',
            session_id: 's1',
            role: 'assistant',
            content: '当前流式消息',
            displayContent: '当前流式消息',
            streamStatus: 'streaming',
            isStreaming: true,
            isPlaceholder: true,
          }),
        ]}
        streamState={streamState}
        currentMessageId={'assistant-stream-active'}
        thinkingSteps={[]}
        labels={{ noMessages: '开始新对话', sendFirst: '发送第一条消息', thinking: '思考中', stop: '停止' }}
        messagesEndRef={createRef<HTMLDivElement>()}
        onCitationClick={() => {}}
        onStop={() => {}}
        formatTime={() => '10:00'}
      />
    );

    expect(screen.getAllByText('Tools')).toHaveLength(1);
  });

  it('shows stop button only for active assistant stream message', () => {
    render(
      <MessageFeed
        renderMessages={[
          asRenderMessage({
            id: 'assistant-stream-old',
            session_id: 's1',
            role: 'assistant',
            content: '旧流式消息',
            displayContent: '旧流式消息',
            streamStatus: 'streaming',
            isStreaming: true,
            isPlaceholder: false,
          }),
          asRenderMessage({
            id: 'assistant-stream-current',
            session_id: 's1',
            role: 'assistant',
            content: '当前流式消息',
            displayContent: '当前流式消息',
            streamStatus: 'streaming',
            isStreaming: true,
            isPlaceholder: true,
          }),
        ]}
        streamState={createInitialState()}
        currentMessageId={'assistant-stream-current'}
        thinkingSteps={[]}
        labels={{ noMessages: '开始新对话', sendFirst: '发送第一条消息', thinking: '思考中', stop: '停止' }}
        messagesEndRef={createRef<HTMLDivElement>()}
        onCitationClick={() => {}}
        onStop={() => {}}
        formatTime={() => '10:00'}
      />
    );

    expect(screen.getAllByRole('button', { name: '停止' })).toHaveLength(1);
  });
});
