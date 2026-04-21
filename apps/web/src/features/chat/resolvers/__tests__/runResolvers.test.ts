/**
 * Tests for run resolvers.
 */

import { describe, it, expect } from 'vitest';
import {
  resolveRunBadge,
  resolvePhaseProgress,
  resolveConfirmationUI,
  resolveRecoveryUI,
  resolveStepProgress,
  canSendMessage,
} from '@/features/chat/resolvers/runResolvers';
import { createInitialRun } from '@/features/chat/runtime/chatRuntime';
import type { AgentRun, PendingAction, ConfirmationRequest } from '@/features/chat/types/run';

function makeRun(overrides: Partial<AgentRun> = {}): AgentRun {
  return { ...createInitialRun(), ...overrides };
}

describe('resolveRunBadge', () => {
  it('returns gray for idle', () => {
    const badge = resolveRunBadge(makeRun({ phase: 'idle' }));
    expect(badge.color).toBe('gray');
    expect(badge.pulse).toBe(false);
  });

  it('returns blue with pulse for executing', () => {
    const badge = resolveRunBadge(makeRun({ phase: 'executing' }));
    expect(badge.color).toBe('blue');
    expect(badge.pulse).toBe(true);
  });

  it('returns green for completed', () => {
    const badge = resolveRunBadge(makeRun({ phase: 'completed' }));
    expect(badge.color).toBe('green');
  });

  it('returns red for failed', () => {
    const badge = resolveRunBadge(makeRun({ phase: 'failed' }));
    expect(badge.color).toBe('red');
  });
});

describe('resolvePhaseProgress', () => {
  it('returns 0 for idle', () => {
    expect(resolvePhaseProgress(makeRun({ phase: 'idle' }))).toBe(0);
  });

  it('returns 100 for completed', () => {
    expect(resolvePhaseProgress(makeRun({ phase: 'completed' }))).toBe(100);
  });

  it('returns intermediate for executing', () => {
    const p = resolvePhaseProgress(makeRun({ phase: 'executing' }));
    expect(p).toBeGreaterThan(0);
    expect(p).toBeLessThan(100);
  });
});

describe('resolveConfirmationUI', () => {
  it('returns not visible for null', () => {
    expect(resolveConfirmationUI(null).visible).toBe(false);
  });

  it('returns visible with details for confirmation', () => {
    const conf: ConfirmationRequest = {
      confirmationId: 'c1',
      runId: 'r1',
      stepId: 's1',
      reason: 'Dangerous op',
      riskLevel: 'high',
      proposedAction: 'Delete',
      toolName: 'delete_paper',
      payload: {},
    };
    const ui = resolveConfirmationUI(conf);
    expect(ui.visible).toBe(true);
    expect(ui.riskLevel).toBe('high');
    expect(ui.toolName).toBe('delete_paper');
  });
});

describe('resolveRecoveryUI', () => {
  it('returns not visible for empty actions', () => {
    expect(resolveRecoveryUI([]).visible).toBe(false);
  });

  it('returns visible with action buttons', () => {
    const actions: PendingAction[] = [
      { id: '1', type: 'retry' },
      { id: '2', type: 'cancel' },
    ];
    const ui = resolveRecoveryUI(actions);
    expect(ui.visible).toBe(true);
    expect(ui.actions).toHaveLength(2);
    expect(ui.actions[0].label).toBe('重试');
  });
});

describe('resolveStepProgress', () => {
  it('returns 0 for no steps', () => {
    expect(resolveStepProgress(makeRun()).percentage).toBe(0);
  });

  it('calculates percentage', () => {
    const run = makeRun({
      steps: [
        { stepId: '1', runId: 'r', type: 'analyze', title: '', description: '', status: 'completed', order: 0 },
        { stepId: '2', runId: 'r', type: 'retrieve', title: '', description: '', status: 'running', order: 1 },
      ],
    });
    const p = resolveStepProgress(run);
    expect(p.total).toBe(2);
    expect(p.completed).toBe(1);
    expect(p.percentage).toBe(50);
  });
});

describe('canSendMessage', () => {
  it('allows sending in idle', () => {
    expect(canSendMessage(makeRun({ status: 'idle' }))).toBe(true);
  });

  it('blocks sending while running', () => {
    expect(canSendMessage(makeRun({ status: 'running' }))).toBe(false);
  });

  it('allows sending after completion', () => {
    expect(canSendMessage(makeRun({ status: 'completed' }))).toBe(true);
  });
});
