import { beforeEach, describe, expect, it, vi } from 'vitest';

const getMessagesMock = vi.fn();

vi.mock('@scholar-ai/sdk', () => ({
  createChatApi: vi.fn(() => ({
    deleteSession: vi.fn(),
    updateSession: vi.fn(),
  })),
  createChatSessionsApi: vi.fn(() => ({
    getMessages: getMessagesMock,
  })),
}));

vi.mock('@/utils/apiClient', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
  },
}));

vi.mock('./sdkHttpClient', () => ({
  sdkHttpClient: {},
}));

describe('sessionsApi.getSessionMessages', () => {
  beforeEach(() => {
    getMessagesMock.mockReset();
  });

  it('normalizes persisted assistant metadata for chat rehydration', async () => {
    getMessagesMock.mockResolvedValue({
      data: {
        messages: [
          {
            id: 'message-1',
            session_id: 'session-1',
            role: 'assistant',
            content: 'Grounded answer',
            reasoning_content: 'retrieving',
            tool_timeline: [{ id: 'tool-1', tool: 'rag_search' }],
            citations: [{ paper_id: 'paper-1', source_chunk_id: 'chunk-1' }],
            answer_contract: {
              response_type: 'rag',
              answer_mode: 'partial',
              citations: [{ paper_id: 'paper-1', source_chunk_id: 'chunk-1' }],
            },
            stream_status: 'completed',
            tokens_used: 128,
            response_type: 'rag',
            created_at: '2026-05-06T10:00:00Z',
          },
        ],
      },
    });

    const { getSessionMessages } = await import('./sessionsApi');
    const messages = await getSessionMessages('session-1');

    expect(messages[0]).toMatchObject({
      reasoning_content: 'retrieving',
      reasoningBuffer: 'retrieving',
      toolTimeline: [{ id: 'tool-1', tool: 'rag_search' }],
      answerContract: {
        response_type: 'rag',
      },
      streamStatus: 'completed',
      tokensUsed: 128,
      responseType: 'rag',
    });
  });
});
