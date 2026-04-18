import { useAuthStore } from '@/stores/authStore';

function hashString(input: string): number {
  let hash = 0;
  for (let index = 0; index < input.length; index += 1) {
    hash = (hash * 31 + input.charCodeAt(index)) >>> 0;
  }
  return hash;
}

function parseRolloutPercent(value: string | undefined): number {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return 100;
  }
  return Math.min(100, Math.max(0, Math.floor(parsed)));
}

export function getChatWorkspaceRolloutPercent(): number {
  return parseRolloutPercent(readChatWorkspaceRolloutEnv());
}

function readChatWorkspaceRolloutEnv(): string | undefined {
  return import.meta.env.VITE_CHAT_WORKSPACE_V2_ROLLOUT_PERCENT as string | undefined;
}

export function isChatWorkspaceV2EnabledForUser(userId: string | null | undefined): boolean {
  const rollout = getChatWorkspaceRolloutPercent();
  if (rollout >= 100) {
    return true;
  }
  if (rollout <= 0) {
    return false;
  }
  const stableKey = userId || 'anonymous';
  return hashString(stableKey) % 100 < rollout;
}

export function useChatWorkspaceV2Gate(): boolean {
  const user = useAuthStore((state) => state.user);
  return isChatWorkspaceV2EnabledForUser(user?.id || null);
}

export const __rolloutTestUtils = {
  parseRolloutPercent,
  hashString,
};