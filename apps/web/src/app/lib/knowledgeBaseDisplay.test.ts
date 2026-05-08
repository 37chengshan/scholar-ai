import { describe, expect, it } from 'vitest';
import { getKnowledgeBaseDisplayMetadata } from './knowledgeBaseDisplay';

describe('getKnowledgeBaseDisplayMetadata', () => {
  it('preserves production-like labels', () => {
    const result = getKnowledgeBaseDisplayMetadata({
      id: 'kb-1',
      name: '多模态检索工作区',
      description: '围绕图文资料建立检索与问答流程。',
    } as any);

    expect(result).toEqual({
      displayName: '多模态检索工作区',
      displayDescription: '围绕图文资料建立检索与问答流程。',
      isFixtureNormalized: false,
    });
  });

  it('normalizes seeded verification labels into product-facing copy', () => {
    const result = getKnowledgeBaseDisplayMetadata({
      id: 'cf84038c-6cdf-434f-8ec8-c97fe3de396e',
      name: 'Phase2-Online-Verify-2b7aa183',
      description: 'Phase2 online provider verification',
    } as any);

    expect(result.displayName).toBe('研究资料馆 A183');
    expect(result.displayDescription).toBe('围绕已导入论文建立检索、阅读、问答与笔记的研究工作区。');
    expect(result.isFixtureNormalized).toBe(true);
  });
});
