/**
 * AgentStateSidebar Component
 *
 * Enhanced sidebar with 4-state machine visualization (D-04, D-05, D-06).
 * Displays IDLE/RUNNING/WAITING/DONE states with visual indicators.
 *
 * Part of Agent-Native architecture (D-04, D-05, D-06)
 */

import { motion } from 'motion/react';
import {
  Circle,
  Loader2,
  AlertCircle,
  CheckCircle,
  Square,
  Activity,
  Brain,
  Wrench,
} from 'lucide-react';
import { clsx } from 'clsx';
import { useLanguage } from '../contexts/LanguageContext';

/**
 * Agent UI State (4-state machine per D-04)
 */
export type AgentUIState = 'IDLE' | 'RUNNING' | 'WAITING' | 'DONE';

/**
 * State visual configuration
 */
interface StateVisual {
  color: string;
  bgColor: string;
  icon: typeof Circle;
  label: { en: string; zh: string };
}

const STATE_VISUALS: Record<AgentUIState, StateVisual> = {
  IDLE: {
    color: 'text-gray-400',
    bgColor: 'bg-gray-100',
    icon: Circle,
    label: { en: 'Ready for input', zh: '等待输入' },
  },
  RUNNING: {
    color: 'text-primary',
    bgColor: 'bg-primary/10',
    icon: Loader2,
    label: { en: 'Executing', zh: '执行中' },
  },
  WAITING: {
    color: 'text-yellow-500',
    bgColor: 'bg-yellow-50',
    icon: AlertCircle,
    label: { en: 'Awaiting confirmation', zh: '等待确认' },
  },
  DONE: {
    color: 'text-green-600',
    bgColor: 'bg-green-50',
    icon: CheckCircle,
    label: { en: 'Completed', zh: '已完成' },
  },
};

/**
 * Execution step for timeline display
 */
export interface ExecutionStep {
  tool?: string;
  action: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  timestamp?: number;
}

/**
 * AgentStateSidebar props
 */
export interface AgentStateSidebarProps {
  state: AgentUIState;
  currentStep?: string;
  totalTime?: number; // milliseconds
  steps?: ExecutionStep[];
  onStop?: () => void;
  className?: string;
}

/**
 * Get step icon based on action type
 */
function getStepIcon(action: string) {
  if (action.toLowerCase().includes('think') || action.toLowerCase().includes('analyze')) {
    return Brain;
  }
  return Wrench;
}

/**
 * AgentStateSidebar Component
 *
 * Displays agent execution state with 4-state visualization.
 * Shows vertical timeline of execution steps.
 */
export function AgentStateSidebar({
  state,
  currentStep,
  totalTime,
  steps = [],
  onStop,
  className,
}: AgentStateSidebarProps) {
  const { language } = useLanguage();
  const isZh = language === 'zh';

  const visual = STATE_VISUALS[state];
  const Icon = visual.icon;
  const isRunning = state === 'RUNNING';

  const t = {
    agentState: isZh ? 'Agent 状态' : 'Agent State',
    readyForInput: isZh ? '等待输入' : 'Ready for input',
    executing: isZh ? '执行中' : 'Executing',
    awaitingConfirmation: isZh ? '等待确认' : 'Awaiting confirmation',
    completed: isZh ? '已完成' : 'Completed',
    stop: isZh ? '停止' : 'Stop',
    seconds: isZh ? '秒' : 's',
    executionPlan: isZh ? '执行计划' : 'Execution Plan',
  };

  return (
    <div
      className={clsx(
        'w-80 border-l border-border/50 bg-background flex flex-col h-full',
        className
      )}
    >
      {/* Header */}
      <div className="px-4 py-3.5 border-b border-border/50 bg-background/80 backdrop-blur-md sticky top-0 z-10">
        <div className="flex items-center justify-between">
          <h3 className="font-serif text-sm font-bold tracking-tight flex items-center gap-2">
            <Activity className="w-4 h-4 text-primary" />
            {t.agentState}
          </h3>
        </div>
      </div>

      {/* State Display */}
      <div className="p-4 border-b border-border/50">
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className={clsx('rounded-lg p-4', visual.bgColor)}
        >
          <div className="flex items-center gap-3">
            <div className={clsx('w-10 h-10 rounded-full flex items-center justify-center', visual.bgColor)}>
              <Icon className={clsx('w-5 h-5', visual.color, isRunning && 'animate-spin')} />
            </div>
            <div className="flex-1 min-w-0">
              <div className={clsx('text-sm font-bold', visual.color)}>
                {isZh ? visual.label.zh : visual.label.en}
              </div>
              {currentStep && isRunning && (
                <div className="text-xs text-muted-foreground truncate mt-0.5">
                  {currentStep}
                </div>
              )}
            </div>
          </div>

          {/* Stop button for RUNNING state */}
          {isRunning && onStop && (
            <button
              onClick={onStop}
              className="mt-3 w-full flex items-center justify-center gap-2 px-3 py-2 bg-destructive/10 hover:bg-destructive/20 text-destructive rounded-lg transition-colors text-sm font-medium"
            >
              <Square className="w-4 h-4" />
              {t.stop}
            </button>
          )}

          {/* Completion time for DONE state */}
          {state === 'DONE' && totalTime && (
            <div className="mt-2 text-xs text-muted-foreground flex items-center gap-1">
              <Activity className="w-3 h-3" />
              {(totalTime / 1000).toFixed(1)}{t.seconds}
            </div>
          )}
        </motion.div>
      </div>

      {/* Execution Timeline */}
      {steps.length > 0 && (
        <div className="flex-1 overflow-y-auto p-4">
          <div className="text-xs font-bold tracking-wide uppercase text-muted-foreground mb-3">
            {t.executionPlan}
          </div>

          <div className="space-y-0">
            {steps.map((step, idx) => {
              const StepIcon = getStepIcon(step.action);
              const isCurrent = step.status === 'running';
              const isCompleted = step.status === 'completed';
              const isFailed = step.status === 'failed';

              return (
                <div key={idx} className="flex gap-3">
                  {/* Timeline connector */}
                  <div className="flex flex-col items-center">
                    <div
                      className={clsx(
                        'w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0',
                        isCurrent && 'bg-primary/20 ring-2 ring-primary ring-offset-2',
                        isCompleted && 'bg-green-100',
                        isFailed && 'bg-red-100',
                        step.status === 'pending' && 'bg-muted'
                      )}
                    >
                      {isCurrent ? (
                        <Loader2 className="w-4 h-4 text-primary animate-spin" />
                      ) : isCompleted ? (
                        <CheckCircle className="w-4 h-4 text-green-600" />
                      ) : isFailed ? (
                        <AlertCircle className="w-4 h-4 text-red-500" />
                      ) : (
                        <StepIcon className="w-4 h-4 text-muted-foreground" />
                      )}
                    </div>
                    {/* Connector line */}
                    {idx < steps.length - 1 && (
                      <div
                        className={clsx(
                          'w-0.5 flex-1 min-h-[20px]',
                          isCompleted ? 'bg-green-200' : 'bg-border/50'
                        )}
                      />
                    )}
                  </div>

                  {/* Step content */}
                  <div className="flex-1 pb-4">
                    <div
                      className={clsx(
                        'text-sm font-medium',
                        isCurrent && 'text-primary',
                        isCompleted && 'text-green-600',
                        isFailed && 'text-red-500',
                        step.status === 'pending' && 'text-muted-foreground'
                      )}
                    >
                      {step.action}
                    </div>
                    {step.tool && (
                      <div className="text-xs text-muted-foreground mt-0.5">
                        {step.tool}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Empty state */}
      {steps.length === 0 && (
        <div className="flex-1 flex items-center justify-center p-4">
          <div className="text-center">
            <Circle className="w-8 h-8 text-muted-foreground/30 mx-auto mb-2" />
            <p className="text-sm text-muted-foreground">
              {t.readyForInput}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

export type { AgentStateSidebarProps as AgentStateSidebarPropsType };