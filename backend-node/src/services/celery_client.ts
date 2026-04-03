/**
 * Celery client for triggering Python tasks from Node.js.
 *
 * Uses HTTP calls to Python FastAPI service to trigger Celery tasks.
 *
 * Phase 11: Batch upload + concurrent processing infrastructure.
 */

import axios from 'axios';
import { logger } from '../utils/logger';

const PYTHON_SERVICE_URL = process.env.AI_SERVICE_URL || 'http://localhost:8000';

/**
 * Trigger Celery task to retry a single failed paper.
 */
export async function retrySinglePdf(paperId: string): Promise<void> {
  try {
    await axios.post(`${PYTHON_SERVICE_URL}/api/tasks/retry/${paperId}`);
    logger.info(`Triggered retry for paper ${paperId}`);
  } catch (error) {
    logger.error(`Failed to trigger retry for paper ${paperId}:`, error);
    throw error;
  }
}

/**
 * Trigger Celery task to retry all failed papers in a batch.
 */
export async function retryBatchFailedPapers(batchId: string): Promise<void> {
  try {
    await axios.post(`${PYTHON_SERVICE_URL}/api/tasks/retry-batch/${batchId}`);
    logger.info(`Triggered batch retry for batch ${batchId}`);
  } catch (error) {
    logger.error(`Failed to trigger batch retry for batch ${batchId}:`, error);
    throw error;
  }
}

/**
 * Trigger Celery task to start processing a batch.
 */
export async function triggerBatchProcessing(batchId: string): Promise<void> {
  try {
    await axios.post(`${PYTHON_SERVICE_URL}/api/tasks/process-batch/${batchId}`);
    logger.info(`Triggered batch processing for batch ${batchId}`);
  } catch (error) {
    logger.error(`Failed to trigger batch processing for batch ${batchId}:`, error);
    throw error;
  }
}