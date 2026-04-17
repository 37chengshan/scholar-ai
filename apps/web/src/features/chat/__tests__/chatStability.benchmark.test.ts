import { describe, expect, it } from 'vitest';

import { chatStabilityCases } from '@/benchmarks/chat/chatStability.cases';


describe('chat stability benchmark cases', () => {
  it('has deterministic chat benchmark fixtures', () => {
    expect(chatStabilityCases.length).toBeGreaterThan(0);
    for (const testCase of chatStabilityCases) {
      expect(testCase.id).toContain('chat.');
      expect(testCase.expected.requiresStreaming).toBe(true);
    }
  });
});
