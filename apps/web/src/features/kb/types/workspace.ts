export type KnowledgeWorkspacePanel =
  | 'papers'
  | 'import-status'
  | 'search'
  | 'chat'
  | 'runs';

export type KnowledgeWorkspaceScope = 'knowledge_base';

export interface KnowledgeRunSummary {
  id: string;
  title: string;
  updatedAt?: string;
}

export interface EvidenceHit {
  id: string;
  paperId: string;
  paperTitle?: string | null;
  content: string;
  page?: number | null;
  score: number;
}

export interface ImportActivitySummary {
  runningCount: number;
  completedCount: number;
  failedCount: number;
}

export interface KnowledgeWorkspaceState {
  scope: KnowledgeWorkspaceScope;
  panel: KnowledgeWorkspacePanel;
  kbId: string;
}
