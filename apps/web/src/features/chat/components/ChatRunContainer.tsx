import { ChatWorkspaceV2 } from '@/features/chat/workspace/ChatWorkspaceV2';
import { ChatLegacy } from './ChatLegacy';
import { useChatWorkspaceV2Gate } from '@/features/chat/workspace/rollout';
import type { AgentRun } from '@/features/chat/types/run';

interface ChatRunContainerProps {
  run: AgentRun;
}

export function ChatRunContainer({ run }: ChatRunContainerProps) {
  const enableV2 = useChatWorkspaceV2Gate();

  return (
    <section
      data-testid="chat-run-container"
      data-run-id={run.runId ?? 'none'}
      data-run-status={run.status}
      data-run-scope={run.scope}
    >
      {enableV2 ? <ChatWorkspaceV2 /> : <ChatLegacy />}
    </section>
  );
}
