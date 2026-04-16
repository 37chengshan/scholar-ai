/**
 * AgentStateSidebar Component
 *
 * Enhanced sidebar with 4-state machine visualization (D-04, D-05, D-06).
 * Displays IDLE/RUNNING/WAITING/DONE states with visual indicators.
 *
 * Phase 4.1: Data Source Priority Implementation
 * - selectedMessage (ChatMessage): Priority data source (user clicked history message)
 * - currentRunningState (ChatStreamState): Fallback data source (current streaming)
 * - If both empty, show empty state
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
  MessageSquare,
  BookOpen,
  FileText,
  GitCompare,
  Timer,
  Coins,
  BarChart3,
  Zap,
} from 'lucide-react';
import { clsx } from 'clsx';
import { useLanguage } from '../contexts/LanguageContext';
import { ChatMessage } from './ChatMessageCard';
import { ChatStreamState, TaskType, CitationItem } from '../hooks/useChatStream';
import { AgentPhase } from '@/types/chat';

/**
 * Agent UI State (4-state machine per D-04)
 */
export type AgentUIState = 'IDLE' | 'RUNNING' | 'WAITING' | 'DONE';

/**
 * Phase to AgentUIState mapping (per plan section 6)
 */
const PHASE_TO_UI_STATE: Record<AgentPhase, AgentUIState> = {
  idle: 'IDLE',
  analyzing: 'RUNNING',
  retrieving: 'RUNNING',
  reading: 'RUNNING',
  tool_calling: 'RUNNING',
  synthesizing: 'RUNNING',
  verifying: 'RUNNING',
  done: 'DONE',
  error: 'DONE',
  cancelled: 'DONE',
};

/**
 * Stream status to AgentUIState mapping
 */
const STREAM_STATUS_TO_UI_STATE: Record<string, AgentUIState> = {
  idle: 'IDLE',
  streaming: 'RUNNING',
  completed: 'DONE',
  error: 'DONE',
  cancelled: 'DONE',
};

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
 * Phase display labels (per plan section 6)
 */
const PHASE_LABELS: Record<AgentPhase, { en: string; zh: string }> = {
  idle: { en: '', zh: '' },
  analyzing: { en: 'Analyzing question', zh: '分析问题中' },
  retrieving: { en: 'Retrieving data', zh: '检索数据中' },
  reading: { en: 'Reading papers', zh: '阅读论文中' },
  tool_calling: { en: 'Executing tools', zh: '调用工具中' },
  synthesizing: { en: 'Organizing answer', zh: '组织回答中' },
  verifying: { en: 'Verifying results', zh: '验证结果中' },
  done: { en: 'Answer complete', zh: '回答完成' },
  error: { en: 'Error occurred', zh: '发生错误' },
  cancelled: { en: 'Cancelled', zh: '已取消' },
};

/**
 * Convert tool status from source types to ExecutionStep status
 */
function convertToolStatus(status: string): 'pending' | 'running' | 'completed' | 'failed' {
  if (status === 'success') return 'completed';
  if (status === 'error') return 'failed';
  if (status === 'running') return 'running';
  return 'pending';
}

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
 *
 * Phase 4.1: Data Source Priority
 * - selectedMessage: Priority source (user clicked history message)
 * - currentRunningState: Fallback source (current streaming state)
 */
export interface AgentStateSidebarProps {
  /** Priority data source - user clicked history message */
  selectedMessage?: ChatMessage;
  /** Fallback data source - current running stream state */
  currentRunningState?: ChatStreamState;
  /** Stop button callback */
  onStop?: () => void;
  /** Optional className for styling */
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
 * Task type icon and label configuration
 */
function getTaskTypeInfo(taskType: TaskType, isZh: boolean) {
  const taskTypes: Record<TaskType, { icon: typeof FileText; label: string; labelEn: string }> = {
    single_paper: {
      icon: FileText,
      label: '单论文问答',
      labelEn: 'Single Paper Q&A',
    },
    kb_qa: {
      icon: BookOpen,
      label: '知识库问答',
      labelEn: 'Knowledge Base Q&A',
    },
    compare: {
      icon: GitCompare,
      label: '对比分析',
      labelEn: 'Compare Analysis',
    },
    general: {
      icon: MessageSquare,
      label: '通用对话',
      labelEn: 'General Chat',
    },
  };
  return taskTypes[taskType];
}

/**
 * Format duration in milliseconds to human-readable format
 */
function formatDuration(ms: number | undefined, isZh: boolean): string {
  if (!ms) return '';
  if (ms < 1000) return `${ms}ms`;
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return isZh ? `${seconds}秒` : `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  if (remainingSeconds === 0) return isZh ? `${minutes}分钟` : `${minutes}m`;
  return isZh ? `${minutes}分${remainingSeconds}秒` : `${minutes}m ${remainingSeconds}s`;
}

/**
 * Format cost to readable format
 */
function formatCost(cost: number, isZh: boolean): string {
  if (cost === 0) return isZh ? '免费' : 'Free';
  if (cost < 0.01) return `$${cost.toFixed(4)}`;
  return `$${cost.toFixed(2)}`;
}

/**
 * Convert ChatMessage or ChatStreamState to unified display data
 *
 * Returns all fields needed for the 5 sub-blocks:
 * 1. AgentStatusCard - taskType, phaseLabel, sourceSummary
 * 2. ExecutionTimeline - toolTimeline
 * 3. EvidencePanel - citations
 * 4. PlanPanel - reasoningBuffer (structured plan)
 * 5. SessionMetricsCard - tokensUsed, cost, duration
 */
function toDisplayData(
  selectedMessage?: ChatMessage,
  currentRunningState?: ChatStreamState
): {
  uiState: AgentUIState;
  taskType: TaskType;
  phaseLabel: string;
  reasoningBuffer: string;
  toolTimeline: ExecutionStep[];
  citations: CitationItem[];
  tokensUsed: number;
  cost: number;
  duration?: number;
  isHistorical: boolean;
  messageId?: string;
} | null {
  // Data source priority per Phase 4.1
  const displayData = selectedMessage ?? currentRunningState;

  if (!displayData) {
    return null;
  }

  // Determine if this is historical (selectedMessage) or running (currentRunningState)
  const isHistorical = !!selectedMessage;

  // Handle ChatMessage (historical message)
  if ('id' in displayData && 'role' in displayData) {
    const message = displayData as ChatMessage;
    const streamStatus = message.streamStatus || 'completed';
    const uiState = STREAM_STATUS_TO_UI_STATE[streamStatus] || 'DONE';

    // Get phase label from message
    const phaseLabel = message.phaseLabel ||
      (message.phase && PHASE_LABELS[message.phase as AgentPhase]
        ? (PHASE_LABELS[message.phase as AgentPhase].en)
        : 'Completed');

    // Get task type from message
    const taskType: TaskType = (message.taskType as TaskType) || 'general';

    // Convert toolTimeline if exists
    const toolTimeline: ExecutionStep[] = (message.toolTimeline || []).map(tool => ({
      tool: tool.tool,
      action: tool.label || tool.tool,
      status: convertToolStatus(tool.status),
      timestamp: tool.startedAt,
    }));

    // Convert citations from PaperCitation to CitationItem if needed
    const citations: CitationItem[] = (message.citations || []).map(c => ({
      paper_id: c.paper_id,
      title: c.title,
      authors: [],  // PaperCitation doesn't have authors field
      year: 0,      // PaperCitation doesn't have year field
      snippet: '',  // PaperCitation doesn't have snippet field
      page: c.page,
      score: c.score,
      content_type: 'text' as const,
    }));

    // Metrics - ChatMessage doesn't have these fields, use defaults
    const tokensUsed = 0;
    const cost = 0;
    const duration = message.timestamp ? undefined : undefined;

    return {
      uiState,
      taskType,
      phaseLabel,
      reasoningBuffer: message.reasoningBuffer || '',
      toolTimeline,
      citations,
      tokensUsed,
      cost,
      duration,
      isHistorical,
      messageId: message.id,
    };
  }

  // Handle ChatStreamState (current running)
  if ('messageId' in displayData && 'streamStatus' in displayData) {
    const state = displayData as ChatStreamState;
    const uiState = STREAM_STATUS_TO_UI_STATE[state.streamStatus] ||
      PHASE_TO_UI_STATE[state.currentPhase] || 'IDLE';

    // Get phase label from state
    const phaseLabel = state.phaseLabel ||
      (PHASE_LABELS[state.currentPhase]
        ? PHASE_LABELS[state.currentPhase].en
        : 'Preparing');

    // Convert toolTimeline
    const toolTimeline: ExecutionStep[] = state.toolTimeline.map(tool => ({
      tool: tool.tool,
      action: tool.label || tool.tool,
      status: convertToolStatus(tool.status),
      timestamp: tool.startedAt,
    }));

    // Calculate duration if available
    const duration = state.endedAt && state.startedAt
      ? state.endedAt - state.startedAt
      : state.startedAt
        ? Date.now() - state.startedAt
        : undefined;

    return {
      uiState,
      taskType: state.taskType,
      phaseLabel,
      reasoningBuffer: state.reasoningBuffer,
      toolTimeline,
      citations: state.citations,
      tokensUsed: state.tokensUsed,
      cost: state.cost,
      duration,
      isHistorical,
      messageId: state.messageId,
    };
  }

  return null;
}

/**
 * AgentStateSidebar Component
 *
 * Phase 4.1: Implements data source priority:
 * 1. selectedMessage (ChatMessage): Priority - user clicked history message
 * 2. currentRunningState (ChatStreamState): Fallback - current streaming state
 * 3. If both empty, show empty state
 *
 * Displays agent execution state with 4-state visualization.
 * Shows vertical timeline of execution steps.
 */
export function AgentStateSidebar({
  selectedMessage,
  currentRunningState,
  onStop,
  className,
}: AgentStateSidebarProps) {
  const { language } = useLanguage();
  const isZh = language === 'zh';

  // Apply data source priority
  const displayInfo = toDisplayData(selectedMessage, currentRunningState);

  // Empty state - no data source available
  if (!displayInfo) {
    return (
      <div
        className={clsx(
          'w-80 border-l border-border/50 bg-background flex flex-col h-full',
          className
        )}
      >
        {/* Header */}
        <div className="px-4 py-3.5 border-b border-border/50 bg-background/80 backdrop-blur-md sticky top-0 z-10">
          <h3 className="font-serif text-sm font-bold tracking-tight flex items-center gap-2">
            <Activity className="w-4 h-4 text-primary" />
            {isZh ? 'Agent 状态' : 'Agent State'}
          </h3>
        </div>

        {/* Empty state */}
        <div className="flex-1 flex items-center justify-center p-4">
          <div className="text-center text-muted-foreground">
            <Circle className="w-8 h-8 mx-auto mb-3 opacity-30" />
            <p className="text-xs">
              {isZh ? '选择一条消息查看详情' : 'Select a message to view details'}
            </p>
          </div>
        </div>
      </div>
    );
  }

  const {
    uiState,
    taskType,
    phaseLabel,
    reasoningBuffer,
    toolTimeline,
    citations,
    tokensUsed,
    cost,
    duration,
    isHistorical,
  } = displayInfo;

  const visual = STATE_VISUALS[uiState];
  const Icon = visual.icon;
  const isRunning = uiState === 'RUNNING';
  const taskInfo = getTaskTypeInfo(taskType, isZh);
  const TaskIcon = taskInfo.icon;

  const t = {
    agentState: isZh ? 'Agent 状态' : 'Agent State',
    stop: isZh ? '停止' : 'Stop',
    seconds: isZh ? '秒' : 's',
    // Sub-block labels
    taskOverview: isZh ? '任务概览' : 'Task Overview',
    executionTimeline: isZh ? '执行时间线' : 'Execution Timeline',
    sourcesEvidence: isZh ? '来源与证据' : 'Sources & Evidence',
    taskBreakdown: isZh ? '任务拆解' : 'Task Breakdown',
    sessionMetrics: isZh ? '会话指标' : 'Session Metrics',
    // Status labels
    thinking: isZh ? '正在思考中...' : 'Thinking...',
    mayTakeTime: isZh ? '这可能需要几秒钟' : 'This may take a few seconds',
    historicalMessage: isZh ? '历史消息' : 'Historical Message',
    startConversation: isZh ? '开始对话以查看执行步骤' : 'Start a conversation to see execution steps',
    noReasoningContent: isZh ? '无推理内容' : 'No reasoning content',
    noCitations: isZh ? '无引用来源' : 'No citations',
    noTools: isZh ? '无工具调用' : 'No tool calls',
    // Metrics labels
    tokensUsed: isZh ? 'Tokens 使用' : 'Tokens Used',
    estimatedCost: isZh ? '预估成本' : 'Estimated Cost',
    executionTime: isZh ? '执行时长' : 'Execution Time',
    toolsCalled: isZh ? '工具调用' : 'Tools Called',
    citationsCount: isZh ? '引用数量' : 'Citations',
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
          {isHistorical && (
            <span className="text-xs text-muted-foreground flex items-center gap-1">
              <MessageSquare className="w-3 h-3" />
              {t.historicalMessage}
            </span>
          )}
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
              {phaseLabel && isRunning && (
                <div className="text-xs text-muted-foreground truncate mt-0.5">
                  {phaseLabel}
                </div>
              )}
            </div>
          </div>

          {/* Stop button for RUNNING state (only for current running, not historical) */}
          {isRunning && onStop && !isHistorical && (
            <button
              onClick={onStop}
              className="mt-3 w-full flex items-center justify-center gap-2 px-3 py-2 bg-destructive/10 hover:bg-destructive/20 text-destructive rounded-lg transition-colors text-sm font-medium"
            >
              <Square className="w-4 h-4" />
              {t.stop}
            </button>
          )}

          {/* Completion time for DONE state */}
          {uiState === 'DONE' && duration && (
            <div className="mt-2 text-xs text-muted-foreground flex items-center gap-1">
              <Activity className="w-3 h-3" />
              {formatDuration(duration, isZh)}
            </div>
          )}
        </motion.div>
      </div>

      {/* Scrollable content area with 5 sub-blocks */}
      <div className="flex-1 overflow-y-auto">
        {/* ==================== */}
        {/* 1. AgentStatusCard - Task Overview */}
        {/* ==================== */}
        <div className="px-4 py-3 border-b border-border/50">
          <div className="text-xs font-bold tracking-wide uppercase text-muted-foreground mb-3 flex items-center gap-1.5">
            <Zap className="w-3 h-3" />
            {t.taskOverview}
          </div>
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
              <TaskIcon className="w-4 h-4 text-primary" />
            </div>
            <div className="flex-1">
              <div className="text-sm font-medium text-foreground">
                {isZh ? taskInfo.label : taskInfo.labelEn}
              </div>
              {phaseLabel && (
                <div className="text-xs text-muted-foreground mt-0.5">
                  {phaseLabel}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* ==================== */}
        {/* 2. ExecutionTimeline - Tool Timeline */}
        {/* ==================== */}
        <div className="px-4 py-3 border-b border-border/50">
          <div className="text-xs font-bold tracking-wide uppercase text-muted-foreground mb-3 flex items-center gap-1.5">
            <Wrench className="w-3 h-3" />
            {t.executionTimeline}
            {toolTimeline.length > 0 && (
              <span className="ml-auto text-xs font-normal text-primary">
                {toolTimeline.length}
              </span>
            )}
          </div>
          {toolTimeline.length > 0 ? (
            <div className="space-y-2">
              {toolTimeline.map((step, idx) => {
                const StepIcon = getStepIcon(step.action);
                const isCurrent = step.status === 'running';
                const isCompleted = step.status === 'completed';
                const isFailed = step.status === 'failed';

                return (
                  <motion.div
                    key={idx}
                    initial={{ opacity: 0, x: -4 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.15, delay: idx * 0.05 }}
                    className="flex items-center gap-2"
                  >
                    {/* Status indicator */}
                    <div
                      className={clsx(
                        'w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0',
                        isCurrent && 'bg-primary/20',
                        isCompleted && 'bg-green-100',
                        isFailed && 'bg-red-100',
                        step.status === 'pending' && 'bg-muted/50'
                      )}
                    >
                      {isCurrent ? (
                        <Loader2 className="w-3 h-3 text-primary animate-spin" />
                      ) : isCompleted ? (
                        <CheckCircle className="w-3 h-3 text-green-600" />
                      ) : isFailed ? (
                        <AlertCircle className="w-3 h-3 text-red-500" />
                      ) : (
                        <StepIcon className="w-3 h-3 text-muted-foreground" />
                      )}
                    </div>
                    {/* Tool info */}
                    <div className="flex-1 min-w-0">
                      <div
                        className={clsx(
                          'text-xs font-medium truncate',
                          isCurrent && 'text-primary',
                          isCompleted && 'text-green-600',
                          isFailed && 'text-red-500',
                          step.status === 'pending' && 'text-muted-foreground'
                        )}
                      >
                        {step.action}
                      </div>
                      {step.tool && (
                        <div className="text-xs text-muted-foreground truncate">
                          {step.tool}
                        </div>
                      )}
                    </div>
                  </motion.div>
                );
              })}
            </div>
          ) : (
            <div className="text-xs text-muted-foreground py-2">
              {isRunning ? t.thinking : t.noTools}
            </div>
          )}
        </div>

        {/* ==================== */}
        {/* 3. EvidencePanel - Sources & Citations */}
        {/* ==================== */}
        <div className="px-4 py-3 border-b border-border/50">
          <div className="text-xs font-bold tracking-wide uppercase text-muted-foreground mb-3 flex items-center gap-1.5">
            <BookOpen className="w-3 h-3" />
            {t.sourcesEvidence}
            {citations.length > 0 && (
              <span className="ml-auto text-xs font-normal text-primary">
                {citations.length}
              </span>
            )}
          </div>
          {citations.length > 0 ? (
            <div className="space-y-2">
              {citations.slice(0, 5).map((citation, idx) => (
                <motion.div
                  key={citation.paper_id || idx}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.15, delay: idx * 0.03 }}
                  className="flex items-start gap-2"
                >
                  <BookOpen className="w-3 h-3 text-purple-400 mt-0.5 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-medium text-foreground truncate">
                      {citation.title}
                    </div>
                    <div className="text-xs text-muted-foreground mt-0.5">
                      {citation.page && (
                        <span>
                          {isZh ? `页码: ${citation.page}` : `Page: ${citation.page}`}
                        </span>
                      )}
                      {citation.score > 0 && (
                        <span className="ml-2">
                          {isZh ? `相关度: ${Math.round(citation.score * 100)}%` : `Relevance: ${Math.round(citation.score * 100)}%`}
                        </span>
                      )}
                    </div>
                  </div>
                </motion.div>
              ))}
              {citations.length > 5 && (
                <div className="text-xs text-muted-foreground">
                  {isZh ? `还有 ${citations.length - 5} 个来源...` : `${citations.length - 5} more sources...`}
                </div>
              )}
            </div>
          ) : (
            <div className="text-xs text-muted-foreground py-2">
              {t.noCitations}
            </div>
          )}
        </div>

        {/* ==================== */}
        {/* 4. PlanPanel - Task Breakdown / Reasoning */}
        {/* ==================== */}
        {reasoningBuffer && (
          <div className="px-4 py-3 border-b border-border/50">
            <div className="text-xs font-bold tracking-wide uppercase text-muted-foreground mb-3 flex items-center gap-1.5">
              <Brain className="w-3 h-3" />
              {t.taskBreakdown}
            </div>
            <div className="max-h-48 overflow-y-auto bg-muted/30 rounded-lg p-3">
              <div className="text-xs text-muted-foreground whitespace-pre-wrap leading-relaxed">
                {reasoningBuffer.length > 500
                  ? reasoningBuffer.slice(0, 500) + '...'
                  : reasoningBuffer}
              </div>
            </div>
          </div>
        )}

        {/* ==================== */}
        {/* 5. SessionMetricsCard - Metrics Statistics */}
        {/* ==================== */}
        <div className="px-4 py-3">
          <div className="text-xs font-bold tracking-wide uppercase text-muted-foreground mb-3 flex items-center gap-1.5">
            <BarChart3 className="w-3 h-3" />
            {t.sessionMetrics}
          </div>
          <div className="grid grid-cols-2 gap-3">
            {/* Tokens Used */}
            <div className="flex items-center gap-2 bg-muted/20 rounded-lg p-2">
              <Coins className="w-3 h-3 text-blue-500" />
              <div>
                <div className="text-xs text-muted-foreground">
                  {t.tokensUsed}
                </div>
                <div className="text-sm font-medium text-foreground">
                  {tokensUsed > 0 ? tokensUsed.toLocaleString() : '-'}
                </div>
              </div>
            </div>
            {/* Estimated Cost */}
            <div className="flex items-center gap-2 bg-muted/20 rounded-lg p-2">
              <Coins className="w-3 h-3 text-green-500" />
              <div>
                <div className="text-xs text-muted-foreground">
                  {t.estimatedCost}
                </div>
                <div className="text-sm font-medium text-foreground">
                  {formatCost(cost, isZh)}
                </div>
              </div>
            </div>
            {/* Execution Time */}
            <div className="flex items-center gap-2 bg-muted/20 rounded-lg p-2">
              <Timer className="w-3 h-3 text-purple-500" />
              <div>
                <div className="text-xs text-muted-foreground">
                  {t.executionTime}
                </div>
                <div className="text-sm font-medium text-foreground">
                  {formatDuration(duration, isZh) || '-'}
                </div>
              </div>
            </div>
            {/* Tools Called */}
            <div className="flex items-center gap-2 bg-muted/20 rounded-lg p-2">
              <Wrench className="w-3 h-3 text-orange-500" />
              <div>
                <div className="text-xs text-muted-foreground">
                  {t.toolsCalled}
                </div>
                <div className="text-sm font-medium text-foreground">
                  {toolTimeline.length}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export type { AgentStateSidebarProps as AgentStateSidebarPropsType };