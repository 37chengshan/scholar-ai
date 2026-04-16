import type { ChatMode, ChatScope } from '@scholar-ai/types';

export interface ChatStreamParams {
  sessionId: string;
  message: string;
  mode?: ChatMode;
  scope?: ChatScope | null;
  context?: Record<string, unknown>;
}

export function buildChatStreamBody(params: ChatStreamParams): Record<string, unknown> {
  const body: Record<string, unknown> = {
    session_id: params.sessionId,
    message: params.message,
    mode: params.mode ?? 'auto',
  };

  if (params.scope) {
    body.scope = params.scope;
  }

  if (params.context) {
    body.context = params.context;
  }

  return body;
}
