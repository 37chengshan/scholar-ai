import type { PaginationParams } from '../common/pagination';

export interface KnowledgeBaseDto {
  id: string;
  userId: string;
  name: string;
  description: string;
  category: string;
  paperCount: number;
  chunkCount: number;
  entityCount: number;
  embeddingModel: string;
  parseEngine: string;
  chunkStrategy: string;
  enableGraph: boolean;
  enableImrad: boolean;
  enableChartUnderstanding: boolean;
  enableMultimodalSearch: boolean;
  enableComparison: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface KnowledgeBaseCreateDto {
  name: string;
  description?: string;
  category?: string;
  embeddingModel?: string;
  parseEngine?: string;
  chunkStrategy?: string;
  enableGraph?: boolean;
  enableImrad?: boolean;
  enableChartUnderstanding?: boolean;
  enableMultimodalSearch?: boolean;
  enableComparison?: boolean;
}

export interface KnowledgeBaseListParams extends PaginationParams {
  search?: string;
  category?: string;
  sortBy?: 'updated' | 'papers' | 'name';
}

export interface KnowledgeBaseListResponse {
  knowledgeBases: KnowledgeBaseDto[];
  total: number;
  limit: number;
}

export interface KnowledgeBasePaperDto {
  id: string;
  title: string;
  authors: string[];
  year?: number | null;
  venue?: string | null;
  status: 'pending' | 'processing' | 'completed' | 'failed' | string;
  chunkCount: number;
  entityCount: number;
  createdAt?: string | null;
  updatedAt?: string | null;
}

export interface KnowledgeBaseSearchHitDto {
  id: string;
  paperId: string;
  paperTitle?: string | null;
  content: string;
  section?: string;
  page?: number;
  score: number;
}

export interface StorageStatsDto {
  kbCount: number;
  paperCount: number;
  chunkCount: number;
  estimatedStorageMB: number;
  storageLimitMB: number;
}
