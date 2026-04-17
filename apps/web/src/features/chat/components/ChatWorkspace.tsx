import { ChatLegacy } from './ChatLegacy';
import { useChatWorkspace } from '@/features/chat/hooks/useChatWorkspace';

export function ChatWorkspace() {
  const { scopeState } = useChatWorkspace();

  return (
    <section data-testid="chat-workspace-root" data-scope={scopeState.scopeType ?? 'none'}>
      <ChatLegacy />
    </section>
  );
}
