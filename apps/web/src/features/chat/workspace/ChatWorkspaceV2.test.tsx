import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

let mockStreamState: any;
let mockCurrentSession: any;
let mockSessionMessages: any[];
let mockCreateSession: any;
let mockWorkspaceState: any;

vi.mock('react-router', () => ({
  useNavigate: () => vi.fn(),
  useSearchParams: () => [new URLSearchParams(), vi.fn()],
}));

vi.mock('@/app/contexts/LanguageContext', () => ({
  useLanguage: () => ({ language: 'zh' }),
}));

vi.mock('@/services/chatApi', () => ({
  streamMessage: vi.fn(),
}));

vi.mock('@/features/workflow/components/WorkflowShell', () => ({
  WorkflowShell: () => <div>workflow-shell</div>,
}));

vi.mock('@/app/components/ScopeBanner', () => ({
  ScopeBanner: () => <div>scope-banner</div>,
}));

vi.mock('@/features/chat/components/workbench/RunHeader', () => ({
  RunHeader: () => <div>run-header</div>,
}));

vi.mock('@/features/chat/components/ChatRightPanel', () => ({
  ChatRightPanel: () => <div>right-panel</div>,
}));

vi.mock('@/app/components/ConfirmationDialog', () => ({
  ConfirmationDialog: () => null,
}));

vi.mock('@/app/components/ConfirmDialog', () => ({
  ConfirmDialog: () => null,
}));

vi.mock('@/features/chat/components/message-feed/MessageFeed', () => ({
  MessageFeed: ({ renderMessages }: { renderMessages: Array<{ displayContent?: string; content?: string }> }) => (
    <div>
      {renderMessages.map((message, index) => (
        <div key={`msg-${index}`}>{message.displayContent || message.content || ''}</div>
      ))}
    </div>
  ),
}));

vi.mock('@/features/chat/components/composer-input/ComposerInput', () => ({
  ComposerInput: ({ onSend }: { onSend: () => void }) => (
    <button type="button" onClick={onSend}>send</button>
  ),
}));

vi.mock('@/features/chat/hooks/usePinnedBottom', () => ({
  usePinnedBottom: () => ({
    isPinnedToBottom: true,
    maybeFollowBottom: vi.fn(),
    alignToBottom: vi.fn(),
  }),
}));

vi.mock('@/features/chat/hooks/useChatWorkspace', () => ({
  useChatWorkspace: () => mockWorkspaceState,
}));

vi.mock('@/features/chat/hooks/useChatScopeController', () => ({
  useChatScopeController: () => ({
    scope: { type: 'general', id: null, title: '' },
    scopeLoading: false,
    handleExitScope: vi.fn(),
  }),
}));

vi.mock('@/features/chat/hooks/useChatSessionController', () => ({
  useChatSessionController: () => ({
    handleNewSession: vi.fn(async () => null),
    handleSwitchSession: vi.fn(async () => {}),
    handleDeleteSession: vi.fn(),
    confirmDeleteSession: vi.fn(),
    cancelDeleteSession: vi.fn(),
  }),
}));

vi.mock('@/features/chat/hooks/useChatRuntimeBridge', () => ({
  useChatRuntimeBridge: () => ({
    ingestRuntimeEvent: vi.fn(),
    handleConfirmation: vi.fn(),
  }),
}));

vi.mock('@/features/chat/runtime/useRuntime', () => ({
  useRuntime: () => ({ run: null, resetRun: vi.fn() }),
}));

vi.mock('@/app/hooks/useSessions', () => ({
  useSessions: () => ({
    sessions: mockCurrentSession ? [mockCurrentSession] : [],
    currentSession: mockCurrentSession,
    messages: mockSessionMessages,
    loading: false,
    createSession: mockCreateSession,
    switchSession: vi.fn(async () => {}),
    deleteSession: vi.fn(async () => true),
  }),
}));

vi.mock('@/features/chat/hooks/useChatStreaming', () => ({
  useChatStreaming: () => ({
    streamState: mockStreamState,
    dispatch: vi.fn(),
    resetRun: vi.fn(),
    handleSSEEvent: vi.fn(),
    forceFlush: vi.fn(),
    getBufferedContent: vi.fn(() => ({
      content: mockStreamState.contentBuffer || '',
      reasoning: mockStreamState.reasoningBuffer || '',
    })),
    currentMessageId: mockWorkspaceState.streamingMessageId,
    confirmation: null,
    resetConfirmation: vi.fn(),
    setCurrentMessageId: vi.fn(),
    startRun: vi.fn(),
    stopRun: vi.fn(),
  }),
}));

import { ChatWorkspaceV2 } from '@/features/chat/workspace/ChatWorkspaceV2';

function buildWorkspaceState(overrides: Record<string, unknown> = {}) {
  return {
    mode: 'auto',
    composerDraft: '你好',
    rightPanelOpen: false,
    showDeleteConfirm: false,
    pendingDeleteSessionId: null,
    streamingMessageId: null,
    setMode: vi.fn(),
    setComposerDraft: vi.fn(),
    setRightPanelOpen: vi.fn(),
    openDeleteConfirm: vi.fn(),
    closeDeleteConfirm: vi.fn(),
    setStreamingMessageId: vi.fn(),
    setIsPinnedToBottom: vi.fn(),
    setScope: vi.fn(),
    setActiveRun: vi.fn(),
    setSelectedRunId: vi.fn(),
    setActiveRunStatus: vi.fn(),
    setPendingActions: vi.fn(),
    setRecoveryBannerVisible: vi.fn(),
    setRunArtifactsPanelOpen: vi.fn(),
    ...overrides,
  };
}

function buildStreamState(overrides: Record<string, unknown> = {}) {
  return {
    streamStatus: 'idle',
    contentBuffer: '',
    reasoningBuffer: '',
    toolTimeline: [],
    citations: [],
    tokensUsed: 0,
    cost: 0,
    startedAt: undefined,
    ...overrides,
  };
}

describe('ChatWorkspaceV2', () => {
  beforeEach(() => {
    mockStreamState = buildStreamState();
    mockCurrentSession = null;
    mockSessionMessages = [];
    mockCreateSession = vi.fn(async () => ({
      id: 'session-1',
      title: 'session-1',
      status: 'active',
      messageCount: 0,
      createdAt: new Date().toISOString(),
    }));
    mockWorkspaceState = buildWorkspaceState();
  });

  it('shows assistant placeholder immediately after sending simple message', async () => {
    let resolveSession: ((value: any) => void) | null = null;
    mockCreateSession = vi.fn(() => new Promise((resolve) => {
      resolveSession = resolve;
    }));

    const user = userEvent.setup();
    render(<ChatWorkspaceV2 />);

    await user.click(screen.getByRole('button', { name: 'send' }));

    expect(screen.getByText('正在检索...')).toBeInTheDocument();

    await act(async () => {
      resolveSession?.({
        id: 'session-1',
        title: 'session-1',
        status: 'active',
        messageCount: 0,
        createdAt: new Date().toISOString(),
      });
      await Promise.resolve();
    });
  });

  it('renders first message chunk content ahead of runtime metadata updates', () => {
    mockCurrentSession = {
      id: 'session-1',
      title: 'session-1',
      status: 'active',
      messageCount: 1,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    mockWorkspaceState = buildWorkspaceState({ streamingMessageId: 'assistant-1', composerDraft: '' });
    mockStreamState = buildStreamState({
      streamStatus: 'streaming',
      contentBuffer: '首个 message chunk',
      reasoningBuffer: '正在推理',
      toolTimeline: [{ id: 'tool-1', tool: 'search_docs', label: '检索', status: 'running', startedAt: Date.now() }],
    });

    mockSessionMessages = [
      {
        id: 'assistant-1',
        session_id: 'session-1',
        role: 'assistant',
        content: '',
        created_at: new Date().toISOString(),
        streamStatus: 'streaming',
      },
    ];

    render(<ChatWorkspaceV2 />);

    expect(screen.getByText('首个 message chunk')).toBeInTheDocument();
  });
});
