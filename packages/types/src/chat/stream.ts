export enum StreamEventType {
  SESSION_START = 'session_start',
  ROUTING_DECISION = 'routing_decision',
  PHASE = 'phase',
  REASONING = 'reasoning',
  MESSAGE = 'message',
  TOOL_CALL = 'tool_call',
  TOOL_RESULT = 'tool_result',
  CITATION = 'citation',
  CONFIRMATION_REQUIRED = 'confirmation_required',
  CANCEL = 'cancel',
  ERROR = 'error',
  DONE = 'done',
  HEARTBEAT = 'heartbeat',
  THINKING_STATUS = 'thinking_status',
  STEP_PROGRESS = 'step_progress',
  THOUGHT = 'thought'
}

export interface StreamEventEnvelope<T = unknown> {
  event: StreamEventType | string;
  data: T;
  message_id: string;
}

export interface SessionStartEventData {
  session_id: string;
  task_type: 'single_paper' | 'kb_qa' | 'compare' | 'general';
  message_id: string;
}

export interface RoutingDecisionEventData {
  route?: 'rag' | 'knowledge_graph' | 'hybrid' | 'external_search' | 'clarification';
  decision?: 'simple' | 'complex' | 'agent';
  confidence: number;
  reason: string;
  estimated_steps?: number;
  alternatives?: Array<{ route: string; confidence: number }>;
}

export interface ReasoningEventData {
  delta: string;
  seq: number;
}

export interface MessageEventData {
  delta: string;
  seq: number;
}

export interface ToolCallEventData {
  id: string;
  tool: string;
  label: string;
  status: 'running';
}

export interface ToolResultEventData {
  id: string;
  tool: string;
  label: string;
  status: 'success' | 'failed';
  summary?: string;
}

export interface DoneEventData {
  finish_reason: 'stop' | 'tool_calls' | 'length' | 'cancel';
  tokens_used?: number;
  cost?: number;
  total_time_ms?: number;
  iterations?: number;
  citations?: Array<Record<string, unknown>>;
}

export interface ErrorEventData {
  code: string;
  message: string;
  recoverable: boolean;
}
