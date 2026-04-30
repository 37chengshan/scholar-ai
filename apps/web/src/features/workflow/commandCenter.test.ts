import { describe, expect, it } from 'vitest';
import { buildKnowledgeBaseReadinessItems, buildReviewOrCompareCommand, sortResearchCommands } from './commandCenter';

describe('commandCenter', () => {
  it('prioritizes blocked KB readiness items ahead of active and ready items', () => {
    const items = buildKnowledgeBaseReadinessItems({
      kb: {
        id: 'kb-1',
        name: 'KB One',
        paperCount: 2,
        chunkCount: 0,
      } as any,
      importJobs: [
        {
          importJobId: 'job-1',
          status: 'awaiting_user_action',
          stage: 'dedupe',
          dedupe: { status: 'awaiting_decision' },
        } as any,
      ],
      runs: [],
    });

    expect(items[0].id).toBe('kb-1:kb-dedupe');
    expect(items[0].priority).toBe('blocked');
    expect(items[1].priority).not.toBe('blocked');
  });

  it('falls back to a compare command when there is no review run', () => {
    const command = buildReviewOrCompareCommand({
      fallbackPaperIds: ['paper-1', 'paper-2', 'paper-3'],
    });

    expect(command).not.toBeNull();
    expect(command?.category).toBe('compare');
    expect(command?.targetHref).toBe('/compare?paper_ids=paper-1,paper-2,paper-3');
  });

  it('sorts command priorities in blocked-active-ready-recent order', () => {
    const sorted = sortResearchCommands([
      {
        id: 'recent',
        category: 'read',
        priority: 'recent',
        title: 'Recent',
        statusLabel: 'Recent',
        reason: 'recent',
        targetHref: '/read/1',
        targetSurface: 'read',
      },
      {
        id: 'ready',
        category: 'chat',
        priority: 'ready',
        title: 'Ready',
        statusLabel: 'Ready',
        reason: 'ready',
        targetHref: '/chat',
        targetSurface: 'chat',
      },
      {
        id: 'active',
        category: 'kb',
        priority: 'active',
        title: 'Active',
        statusLabel: 'Active',
        reason: 'active',
        targetHref: '/knowledge-bases/kb-1',
        targetSurface: 'kb',
      },
      {
        id: 'blocked',
        category: 'review',
        priority: 'blocked',
        title: 'Blocked',
        statusLabel: 'Blocked',
        reason: 'blocked',
        targetHref: '/knowledge-bases/kb-1?tab=review',
        targetSurface: 'review',
      },
    ]);

    expect(sorted.map((item) => item.id)).toEqual(['blocked', 'active', 'ready', 'recent']);
  });
});
