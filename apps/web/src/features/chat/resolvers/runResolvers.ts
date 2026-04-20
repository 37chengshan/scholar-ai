/**
 * Run Resolvers — Pure functions that derive UI state from AgentRun.
 *
 * Per 战役 B WP3: Pages do NOT compute display logic directly.
 * All UI derivation goes through resolvers.
 */

import type {
  AgentRun,
  RunPhase,
  RunStatus,
  PendingAction,
  ConfirmationRequest,
} from '@/features/chat/types/run';

// ── Phase Display ────────────────────────────────────────

export interface PhaseBadge {
  label: string;
  color: 'gray' | 'blue' | 'yellow' | 'green' | 'red' | 'orange';
  pulse: boolean;
}

const PHASE_BADGE_MAP: Record<RunPhase, PhaseBadge> = {
  idle: { label: '准备就绪', color: 'gray', pulse: false },
  planning: { label: '规划中', color: 'blue', pulse: true },
  executing: { label: '执行中', color: 'blue', pulse: true },
  waiting_for_user: { label: '等待确认', color: 'yellow', pulse: true },
  verifying: { label: '验证中', color: 'blue', pulse: true },
  completed: { label: '完成', color: 'green', pulse: false },
  failed: { label: '失败', color: 'red', pulse: false },
  cancelled: { label: '已取消', color: 'orange', pulse: false },
};

export function resolveRunBadge(run: AgentRun): PhaseBadge {
  return PHASE_BADGE_MAP[run.phase] || PHASE_BADGE_MAP.idle;
}

// ── Phase Progress ───────────────────────────────────────

const PHASE_ORDER: RunPhase[] = [
  'planning', 'executing', 'verifying', 'completed',
];

export function resolvePhaseProgress(run: AgentRun): number {
  if (run.phase === 'idle') return 0;
  if (run.phase === 'completed') return 100;
  if (run.phase === 'failed' || run.phase === 'cancelled') return 0;
  const idx = PHASE_ORDER.indexOf(run.phase);
  if (idx < 0) return 25;
  return Math.round(((idx + 1) / PHASE_ORDER.length) * 100);
}

// ── Confirmation UI ──────────────────────────────────────

export interface ConfirmationUI {
  visible: boolean;
  title: string;
  description: string;
  riskLevel: 'low' | 'medium' | 'high';
  confirmLabel: string;
  rejectLabel: string;
  toolName: string;
}

export function resolveConfirmationUI(
  confirmation: ConfirmationRequest | null
): ConfirmationUI {
  if (!confirmation) {
    return {
      visible: false,
      title: '',
      description: '',
      riskLevel: 'low',
      confirmLabel: '确认',
      rejectLabel: '取消',
      toolName: '',
    };
  }

  const riskLabels: Record<string, string> = {
    high: '⚠️ 高风险操作',
    medium: '⚡ 中风险操作',
    low: '操作确认',
  };

  return {
    visible: true,
    title: riskLabels[confirmation.riskLevel] || '操作确认',
    description: confirmation.reason,
    riskLevel: confirmation.riskLevel,
    confirmLabel: '确认执行',
    rejectLabel: '拒绝',
    toolName: confirmation.toolName,
  };
}

// ── Recovery Actions ─────────────────────────────────────

export interface RecoveryUI {
  visible: boolean;
  actions: Array<{
    id: string;
    label: string;
    variant: 'primary' | 'secondary' | 'danger';
    icon: string;
  }>;
}

const RECOVERY_LABELS: Record<string, { label: string; variant: 'primary' | 'secondary' | 'danger'; icon: string }> = {
  retry: { label: '重试', variant: 'primary', icon: 'RotateCcw' },
  resume: { label: '继续', variant: 'primary', icon: 'Play' },
  cancel: { label: '取消', variant: 'danger', icon: 'X' },
  confirm: { label: '确认', variant: 'primary', icon: 'Check' },
  reject: { label: '拒绝', variant: 'secondary', icon: 'X' },
};

export function resolveRecoveryUI(actions: PendingAction[]): RecoveryUI {
  if (actions.length === 0) {
    return { visible: false, actions: [] };
  }
  return {
    visible: true,
    actions: actions.map(a => ({
      id: a.id,
      ...(RECOVERY_LABELS[a.type] || { label: a.type, variant: 'secondary' as const, icon: 'Circle' }),
    })),
  };
}

// ── Step Progress Summary ────────────────────────────────

export interface StepProgressSummary {
  total: number;
  completed: number;
  running: number;
  failed: number;
  percentage: number;
}

export function resolveStepProgress(run: AgentRun): StepProgressSummary {
  const total = run.steps.length;
  const completed = run.steps.filter(s => s.status === 'completed').length;
  const running = run.steps.filter(s => s.status === 'running').length;
  const failed = run.steps.filter(s => s.status === 'failed').length;
  return {
    total,
    completed,
    running,
    failed,
    percentage: total > 0 ? Math.round((completed / total) * 100) : 0,
  };
}

// ── Can Send Message ─────────────────────────────────────

export function canSendMessage(run: AgentRun): boolean {
  return run.status === 'idle' || run.status === 'completed' || run.status === 'failed' || run.status === 'cancelled';
}
