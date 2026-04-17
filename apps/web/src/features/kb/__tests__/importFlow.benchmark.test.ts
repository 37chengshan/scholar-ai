import { describe, expect, it } from 'vitest';

import { importFlowCases } from '@/benchmarks/kb/importFlow.cases';


describe('import flow benchmark cases', () => {
  it('tracks cancel and refresh expectations', () => {
    expect(importFlowCases.length).toBeGreaterThan(0);
    for (const testCase of importFlowCases) {
      expect(testCase.id).toContain('import.');
      expect(testCase.expected.supportsCancel).toBe(true);
    }
  });
});
