import { describe, expect, it } from 'vitest';
import { __rolloutTestUtils, isChatWorkspaceV2EnabledForUser } from './rollout';

describe('chat workspace rollout helpers', () => {
  it('clamps rollout percentage into 0-100', () => {
    expect(__rolloutTestUtils.parseRolloutPercent('150')).toBe(100);
    expect(__rolloutTestUtils.parseRolloutPercent('-10')).toBe(0);
    expect(__rolloutTestUtils.parseRolloutPercent('40.8')).toBe(40);
    expect(__rolloutTestUtils.parseRolloutPercent('invalid')).toBe(100);
  });

  it('hash is deterministic for same key', () => {
    const first = __rolloutTestUtils.hashString('stable-user');
    const second = __rolloutTestUtils.hashString('stable-user');
    expect(first).toBe(second);
  });

  it('rollout assignment is deterministic for same user', () => {
    const first = isChatWorkspaceV2EnabledForUser('stable-user');
    const second = isChatWorkspaceV2EnabledForUser('stable-user');
    expect(first).toBe(second);
  });
});
