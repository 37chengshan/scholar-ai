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

export interface CitationDto {
  paper_id: string;
  title: string;
  pages?: number[];
  hits?: number;
}
