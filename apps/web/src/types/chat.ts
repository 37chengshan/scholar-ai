/**
 * Chat Type Definitions
 *
 * Shared type definitions for all chat components in Phase 28.
 * Used by ToolCallCard, CitationsPanel, TokenMonitor, ConfirmationDialog,
 * and all 15+ tool-specific components.
 *
 * Phase 5.1: Extended for Thinking refactor with AgentPhase, ToolTimelineItem, CitationItem.
 */

/**
 * Agent processing phase for thinking visualization
 * Per implementation plan v3 Section 3.1
 */
export type AgentPhase =
  | 'idle'
  | 'analyzing'
  | 'retrieving'
  | 'reading'
  | 'tool_calling'
  | 'synthesizing'
  | 'verifying'
  | 'done'
  | 'error'
  | 'cancelled';

/**
 * Stream status for message state machine
 * Per HARD RULE 0.3: idle → streaming → completed/error/cancelled
 */
export type StreamStatus = 'idle' | 'streaming' | 'completed' | 'error' | 'cancelled';

/**
 * Status of a tool call execution
 */
export type ToolCallStatus = 'pending' | 'running' | 'success' | 'error';

/**
 * Tool timeline item for real-time tool tracking
 * Per implementation plan v3 Section 3.1 ChatStreamState.toolTimeline
 */
export interface ToolTimelineItem {
  id: string;
  tool: string;
  label: string;
  status: 'running' | 'success' | 'failed';
  summary?: string;
  startedAt?: number;
  endedAt?: number;
}

/**
 * Citation item for message references
 * Per implementation plan v3 Section 3.1 ChatStreamState.citations
 */
export interface CitationItem {
  paper_id: string;
  title: string;
  pages?: number[];
  hits?: number;
  relevance?: number;
}

/**
 * Represents a tool call made by the Agent during a chat session.
 * Tracks lifecycle from pending → running → success/error.
 */
export interface ToolCall {
  id: string;
  tool: string;
  parameters: Record<string, unknown>;
  status: ToolCallStatus;
  result?: unknown;
  duration?: number;
  startedAt: number;
  completedAt?: number;
}

/**
 * A paper citation returned from RAG search results.
 * Used in CitationsPanel and inline citation markers.
 */
export interface PaperCitation {
  paper_id: string;
  title: string;
  authors: string[];
  year: number;
  journal?: string;
  page: number;
  snippet: string;
  score: number; // 0-1 relevance score
  content_type: 'text' | 'table' | 'figure';
  chunk_id?: string;
}

/**
 * Token usage metrics for a single message or session.
 */
export interface TokenUsage {
  tokensUsed: number;
  cost: number;
  model?: string;
}

/**
 * Display configuration for a tool call in the UI.
 * Per D-04: each tool gets an icon, display name, and description.
 */
export interface ToolCallDisplayConfig {
  icon: string; // lucide-react icon name
  displayName: string;
  description: string;
}

/**
 * Map of all 15+ Agent tools to their display configuration.
 * Used by ToolCallCard to render tool-specific icons and labels.
 * Display names are Chinese defaults; components using useLanguage()
 * can provide English equivalents.
 */
export const TOOL_DISPLAY_CONFIG: Record<string, ToolCallDisplayConfig> = {
  ask_user_confirmation: {
    icon: 'ShieldCheck',
    displayName: '确认请求',
    description: 'Agent需要您的确认',
  },
  upload_paper: {
    icon: 'Upload',
    displayName: '上传论文',
    description: '正在上传并处理论文',
  },
  create_note: {
    icon: 'FilePlus',
    displayName: '创建笔记',
    description: '正在创建新笔记',
  },
  update_note: {
    icon: 'FileEdit',
    displayName: '更新笔记',
    description: '正在更新笔记',
  },
  list_papers: {
    icon: 'List',
    displayName: '论文列表',
    description: '正在检索论文',
  },
  read_paper: {
    icon: 'FileText',
    displayName: '阅读论文',
    description: '正在读取论文内容',
  },
  rag_search: {
    icon: 'Search',
    displayName: 'RAG搜索',
    description: '正在搜索本地知识库',
  },
  external_search: {
    icon: 'Globe',
    displayName: '外部搜索',
    description: '正在搜索外部学术资源',
  },
  extract_references: {
    icon: 'Quote',
    displayName: '提取引用',
    description: '正在提取参考文献',
  },
  list_notes: {
    icon: 'Notebook',
    displayName: '笔记列表',
    description: '正在检索笔记',
  },
  read_note: {
    icon: 'BookOpen',
    displayName: '阅读笔记',
    description: '正在读取笔记内容',
  },
  merge_documents: {
    icon: 'Combine',
    displayName: '合并文档',
    description: '正在合并文档',
  },
  execute_command: {
    icon: 'Terminal',
    displayName: '执行命令',
    description: '正在执行命令',
  },
  show_message: {
    icon: 'MessageSquare',
    displayName: '消息提示',
    description: 'Agent消息',
  },
  delete_paper: {
    icon: 'Trash2',
    displayName: '删除论文',
    description: '正在删除论文',
  },
};
