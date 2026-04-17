import { describe, expect, it } from 'vitest';

import { searchFlowCases } from '@/benchmarks/search/searchFlow.cases';


describe('search flow benchmark cases', () => {
  it('enforces pagination stability expectations', () => {
    expect(searchFlowCases.length).toBeGreaterThan(0);
    for (const testCase of searchFlowCases) {
      expect(testCase.id).toContain('search.');
      expect(testCase.expected.paginationStable).toBe(true);
    }
  });
});
