import { createInitialRun } from '@/features/chat/runtime/chatRuntime';
import { useChatWorkspaceStore } from '@/features/chat/state/chatWorkspaceStore';

export function useChatRun() {
  const activeRun = useChatWorkspaceStore((state) => state.activeRun);
  return { activeRun: activeRun ?? createInitialRun() };
}
