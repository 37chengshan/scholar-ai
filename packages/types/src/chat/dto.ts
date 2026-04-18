export type ChatMode = 'auto' | 'rag' | 'agent';

export interface ChatScope {
  type: 'paper' | 'knowledge_base' | 'general';
  paper_id?: string;
  knowledge_base_id?: string;
}

export interface SessionDto {
  id: string;
  title: string;
  status: string;
  messageCount: number;
  createdAt: string;
  updatedAt?: string;
}

export interface MessageDto {
  id: string;
  session_id: string;
  role: 'user' | 'assistant' | 'tool' | 'system';
  content: string;
  tool_name?: string;
  created_at: string;
}

export type MessageOrder = 'asc' | 'desc';

export interface SessionMessagesPagination {
  has_more: boolean;
  returned: number;
  next_offset: number;
}

export interface SessionMessagesData {
  session_id: string;
  messages: MessageDto[];
  total: number;
  limit: number;
  offset: number;
  order: MessageOrder;
  pagination: SessionMessagesPagination;
}

export interface SessionMessagesResponse {
  success: boolean;
  data: SessionMessagesData;
}

export interface CitationDto {
  paper_id: string;
  title: string;
  pages?: number[];
  hits?: number;
}
