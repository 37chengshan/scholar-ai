/**
 * AI Service Client
 *
 * Handles communication between Node.js gateway and Python AI service.
 * Provides RAG query, PDF parsing, and entity extraction endpoints.
 */

import { HttpClient } from '../utils/httpClient';
import { logger } from '../utils/logger';
import { Errors } from '../middleware/errorHandler';
import { v4 as uuidv4 } from 'uuid';

// Environment configuration
const AI_SERVICE_URL = process.env.AI_SERVICE_URL || 'http://localhost:8000';

// Request/Response types matching Python models
export interface RAGQueryRequest {
  question: string;
  paper_ids?: string[];
  query_type?: 'single' | 'cross_paper' | 'evolution';
  top_k?: number;
  conversation_id?: string;
}

export interface RAGQueryResponse {
  answer: string;
  sources: Array<{
    paper_id: string;
    title?: string;
    chunk_id: string;
    score: number;
    page: number;
    content_preview?: string;
  }>;
  confidence: number;
  conversation_id?: string;
  cached: boolean;
}

export interface AgenticSearchRequest {
  query: string;
  query_type?: 'single' | 'cross_paper' | 'evolution';
  paper_ids?: string[];
  max_rounds?: number;
  top_k?: number;
}

export interface AgenticSearchResponse {
  answer: string;
  sub_questions: Array<{
    question: string;
    answer: string;
    sources: unknown[];
  }>;
  sources: unknown[];
  rounds_executed: number;
  converged: boolean;
  metadata: Record<string, unknown>;
}

class AIService {
  private client: HttpClient;

  constructor() {
    this.client = new HttpClient({
      baseURL: AI_SERVICE_URL,
      timeout: 60000, // 60 seconds for RAG queries
    });
    logger.info(`AI Service client initialized: ${AI_SERVICE_URL}`);
  }

  /**
   * Execute RAG query against Python service
   *
   * The Python service has semantic cache (Plan 02), so similar queries
   * will return cached responses without LLM calls.
   */
  async ragQuery(request: RAGQueryRequest): Promise<RAGQueryResponse> {
    const requestId = uuidv4();
    
    try {
      logger.info('RAG query request', {
        request_id: requestId,
        question: request.question.substring(0, 50),
        paper_count: request.paper_ids?.length || 0,
        query_type: request.query_type,
      });

      const response = await this.client.post<RAGQueryResponse>('/rag/query', {
        question: request.question,
        paper_ids: request.paper_ids || [],
        query_type: request.query_type || 'single',
        top_k: request.top_k || 10,
        conversation_id: request.conversation_id,
      });

      logger.info('RAG query response', {
        request_id: requestId,
        cached: response.cached,
        confidence: response.confidence,
        source_count: response.sources.length,
      });

      return response;

    } catch (error) {
      logger.error('RAG query failed', {
        request_id: requestId,
        error: (error as Error).message,
      });
      throw Errors.serviceUnavailable('AI service unavailable');
    }
  }

  /**
   * Execute agentic search for complex cross-paper queries
   */
  async agenticSearch(request: AgenticSearchRequest): Promise<AgenticSearchResponse> {
    const requestId = uuidv4();
    
    try {
      logger.info('Agentic search request', {
        request_id: requestId,
        query: request.query.substring(0, 50),
        query_type: request.query_type,
      });

      const response = await this.client.post<AgenticSearchResponse>('/rag/agentic', {
        query: request.query,
        query_type: request.query_type || 'single',
        paper_ids: request.paper_ids || [],
        max_rounds: request.max_rounds || 3,
        top_k: request.top_k || 5,
      });

      logger.info('Agentic search response', {
        request_id: requestId,
        rounds: response.rounds_executed,
        converged: response.converged,
      });

      return response;

    } catch (error) {
      logger.error('Agentic search failed', {
        request_id: requestId,
        error: (error as Error).message,
      });
      throw Errors.serviceUnavailable('AI service unavailable');
    }
  }

  /**
   * Health check for Python service
   */
  async healthCheck(): Promise<{ status: string }> {
    try {
      const response = await this.client.get<{ status: string }>('/health');
      return response;
    } catch {
      return { status: 'unhealthy' };
    }
  }
}

// Singleton instance
export const aiService = new AIService();