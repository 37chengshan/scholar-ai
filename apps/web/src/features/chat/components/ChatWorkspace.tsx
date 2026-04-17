import { ChatRunContainer } from './ChatRunContainer';
import { useChatWorkspace } from '@/features/chat/hooks/useChatWorkspace';
import { useChatRun } from '@/features/chat/hooks/useChatRun';

export function ChatWorkspace() {
  const { scopeState } = useChatWorkspace();
  const { activeRun } = useChatRun();

  return (
    <section data-testid="chat-workspace-root" data-scope={scopeState.scopeType ?? 'none'}>
      <ChatRunContainer run={activeRun} />
    </section>
  );
}
