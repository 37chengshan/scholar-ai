import { ChatWorkspaceV2 } from '@/features/chat/workspace/ChatWorkspaceV2';
import type { AgentRun } from '@/features/chat/types/run';

interface ChatRunContainerProps {
  run: AgentRun;
}

export function ChatRunContainer({ run }: ChatRunContainerProps) {
  return (
    <section
      data-testid="chat-run-container"
      data-run-id={run.runId ?? 'none'}
      data-run-status={run.status}
      data-run-scope={run.scope}
    >
      <ChatWorkspaceV2 />
    </section>
  );
}
