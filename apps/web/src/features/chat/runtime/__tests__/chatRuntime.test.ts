/**
 * Tests for chatRuntime reducer and SSE→RunAction mapper.
 */

import { describe, it, expect, vi } from 'vitest';
import {
  runReducer,
  createInitialRun,
  mapSSEToRunAction,
  type RunAction,
} from '@/features/chat/runtime/chatRuntime';
import type { AgentRun } from '@/features/chat/types/run';

describe('runReducer', () => {
  it('initializes with idle state', () => {
    const state = createInitialRun();
    expect(state.status).toBe('idle');
    expect(state.phase).toBe('idle');
    expect(state.steps).toEqual([]);
    expect(state.timeline).toEqual([]);
  });

  it('handles RUN_START', () => {
    const state = runReducer(createInitialRun(), {
      type: 'RUN_START',
      runId: 'r1',
      sessionId: 's1',
      messageId: 'm1',
      scope: 'general',
      objective: 'Test',
      mode: 'auto',
    });
    expect(state.runId).toBe('r1');
    expect(state.status).toBe('running');
    expect(state.phase).toBe('planning');
    expect(state.timeline).toHaveLength(1);
  });

  it('handles RUN_PHASE_CHANGE', () => {
    let state = runReducer(createInitialRun(), {
      type: 'RUN_START',
      runId: 'r1', sessionId: 's1', messageId: 'm1',
      scope: 'general', objective: '', mode: 'auto',
    });
    state = runReducer(state, {
      type: 'RUN_PHASE_CHANGE',
      phase: 'executing',
      label: '执行中',
    });
    expect(state.phase).toBe('executing');
    expect(state.status).toBe('running');
  });

  it('handles STEP_START and STEP_COMPLETE', () => {
    let state = runReducer(createInitialRun(), {
      type: 'RUN_START',
      runId: 'r1', sessionId: 's1', messageId: 'm1',
      scope: 'general', objective: '', mode: 'auto',
    });
    state = runReducer(state, {
      type: 'STEP_START',
      stepId: 'step-1',
      runId: 'r1',
      stepType: 'analyze',
      title: 'Analyzing',
      description: 'desc',
      order: 0,
    });
    expect(state.steps).toHaveLength(1);
    expect(state.steps[0].status).toBe('running');

    state = runReducer(state, {
      type: 'STEP_COMPLETE',
      stepId: 'step-1',
      status: 'completed',
    });
    expect(state.steps[0].status).toBe('completed');
  });

  it('handles RUN_COMPLETE', () => {
    let state = runReducer(createInitialRun(), {
      type: 'RUN_START',
      runId: 'r1', sessionId: 's1', messageId: 'm1',
      scope: 'general', objective: '', mode: 'auto',
    });
    state = runReducer(state, {
      type: 'RUN_COMPLETE',
      status: 'completed',
      tokensUsed: 100,
      cost: 0.01,
    });
    expect(state.status).toBe('completed');
    expect(state.phase).toBe('completed');
  });

  it('generates unique timeline IDs even when Date.now is constant', () => {
    const nowSpy = vi.spyOn(Date, 'now').mockReturnValue(1700000000000);

    let state = runReducer(createInitialRun(), {
      type: 'RUN_START',
      runId: 'r1', sessionId: 's1', messageId: 'm1',
      scope: 'general', objective: '', mode: 'auto',
    });
    state = runReducer(state, {
      type: 'RUN_PHASE_CHANGE',
      phase: 'executing',
      label: 'Executing',
    });
    state = runReducer(state, {
      type: 'CONFIRMATION_REQUEST',
      confirmation: {
        confirmationId: 'c1',
        runId: 'r1',
        stepId: 's1',
        reason: 'Approve',
        riskLevel: 'medium',
        proposedAction: 'Run tool',
        toolName: 'browser',
        payload: {},
      },
    });

    const ids = state.timeline.map((item) => item.id);
    expect(new Set(ids).size).toBe(ids.length);
    nowSpy.mockRestore();
  });

  it('keeps only one terminal timeline item when RUN_COMPLETE is received repeatedly', () => {
    let state = runReducer(createInitialRun(), {
      type: 'RUN_START',
      runId: 'r1', sessionId: 's1', messageId: 'm1',
      scope: 'general', objective: '', mode: 'auto',
    });

    state = runReducer(state, {
      type: 'RUN_COMPLETE',
      status: 'completed',
      tokensUsed: 10,
      cost: 0.001,
    });
    state = runReducer(state, {
      type: 'RUN_COMPLETE',
      status: 'completed',
      tokensUsed: 11,
      cost: 0.0011,
    });

    expect(state.timeline.filter((item) => item.type === 'done')).toHaveLength(1);
  });

  it('handles RECOVERY_AVAILABLE', () => {
    let state = runReducer(createInitialRun(), {
      type: 'RUN_START',
      runId: 'r1', sessionId: 's1', messageId: 'm1',
      scope: 'general', objective: '', mode: 'auto',
    });
    state = runReducer(state, {
      type: 'RECOVERY_AVAILABLE',
      actions: ['retry', 'cancel'],
      context: { error: 'test' },
    });
    expect(state.recoverable).toBe(true);
    expect(state.pendingActions).toHaveLength(2);
  });

  it('adds confirmation actions when confirmation is required', () => {
    const state = runReducer(createInitialRun(), {
      type: 'CONFIRMATION_REQUEST',
      confirmation: {
        confirmationId: 'confirm-1',
        runId: 'r1',
        stepId: 'step-1',
        reason: 'Need approval',
        riskLevel: 'high',
        proposedAction: 'Delete temp files',
        toolName: 'cleanup',
        payload: {},
      },
    });

    expect(state.phase).toBe('waiting_for_user');
    expect(state.pendingActions.map((action) => action.type)).toEqual(['confirm', 'reject']);
  });

  it('clears recovery state when run completes', () => {
    let state = runReducer(createInitialRun(), {
      type: 'RECOVERY_AVAILABLE',
      actions: ['retry', 'cancel'],
      context: { error: 'test' },
    });

    state = runReducer(state, {
      type: 'RUN_COMPLETE',
      status: 'failed',
      tokensUsed: 5,
      cost: 0.001,
    });

    expect(state.recoverable).toBe(false);
    expect(state.pendingActions).toEqual([]);
  });

  it('handles EVIDENCE_ADD', () => {
    const state = runReducer(createInitialRun(), {
      type: 'EVIDENCE_ADD',
      evidence: {
        sourceId: 'src1',
        title: 'Paper A',
        textPreview: 'snippet',
        relevance: 0.9,
      },
    });
    expect(state.evidence).toHaveLength(1);
    expect(state.evidence[0].title).toBe('Paper A');
  });

  it('handles RUN_RESET', () => {
    let state = runReducer(createInitialRun(), {
      type: 'RUN_START',
      runId: 'r1', sessionId: 's1', messageId: 'm1',
      scope: 'general', objective: '', mode: 'auto',
    });
    state = runReducer(state, { type: 'RUN_RESET' });
    expect(state.status).toBe('idle');
    expect(state.runId).toBeNull();
  });
});

describe('mapSSEToRunAction', () => {
  it('maps run_start event', () => {
    const action = mapSSEToRunAction('run_start', {
      run_id: 'r1',
      session_id: 's1',
      message_id: 'm1',
      scope: 'general',
      objective: 'test',
      mode: 'auto',
    });
    expect(action).toBeTruthy();
    expect(action!.type).toBe('RUN_START');
  });

  it('maps run_complete event', () => {
    const action = mapSSEToRunAction('run_complete', {
      status: 'completed',
      tokens_used: 50,
      cost: 0.005,
    });
    expect(action).toBeTruthy();
    expect(action!.type).toBe('RUN_COMPLETE');
  });

  it('maps evidence event', () => {
    const action = mapSSEToRunAction('evidence', {
      source_id: 'src1',
      title: 'Paper',
      text_preview: 'text',
    });
    expect(action).toBeTruthy();
    expect(action!.type).toBe('EVIDENCE_ADD');
  });

  it('maps confirmation_required event', () => {
    const action = mapSSEToRunAction('confirmation_required', {
      confirmation_id: 'confirm-1',
      run_id: 'r1',
      step_id: 'step-1',
      reason: 'Approve tool call',
      tool_name: 'browser',
      parameters: { url: 'https://example.com' },
      risk_level: 'medium',
    });

    expect(action).toBeTruthy();
    expect(action!.type).toBe('CONFIRMATION_REQUEST');
  });

  it('returns null for unknown events', () => {
    const action = mapSSEToRunAction('unknown_event', {});
    expect(action).toBeNull();
  });
});
