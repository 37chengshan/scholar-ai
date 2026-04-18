import { ChatWorkspaceV2 } from '@/features/chat/workspace/ChatWorkspaceV2';

// LEGACY BRIDGE (Plan A W1-W2):
// - ChatLegacy main body has been migrated to ChatWorkspaceV2.
// - Keep this bridge for compatibility during rollout window.
// - Do not add business logic in this file.
export function ChatLegacy() {
  return <ChatWorkspaceV2 />;
}
