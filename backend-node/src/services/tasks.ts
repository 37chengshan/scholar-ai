import { prisma } from '../config/database';
import { logger } from '../utils/logger';

// Task status types matching the 6-state pipeline
export type TaskStatus =
  | 'pending'
  | 'processing_ocr'
  | 'parsing'
  | 'extracting_imrad'
  | 'generating_notes'
  | 'completed'
  | 'failed';

// Task status response
export interface TaskStatusResponse {
  taskId: string;
  paper_id: string;
  status: TaskStatus;
  progress: number;
  storage_key: string;
  error_message: string | null;
  attempts: number;
  created_at: Date;
  updated_at: Date;
  completed_at: Date | null;
}

// Progress mapping for each status
const STATUS_PROGRESS: Record<TaskStatus, number> = {
  pending: 0,
  processing_ocr: 10,
  parsing: 30,
  extracting_imrad: 50,
  generating_notes: 80,
  completed: 100,
  failed: 0,
};

/**
 * Create a new processing task for a paper
 */
export async function createTask(
  paper_id: string,
  storage_key: string
): Promise<TaskStatusResponse> {
  try {
    const task = await prisma.processing_tasks.create({
      data: { id: crypto.randomUUID(), updated_at: new Date(),
        paper_id,
        storage_key,
        status: 'pending',
      },
    });

    logger.info(`Created processing task ${task.id} for paper ${paper_id}`);

    return {
      taskId: task.id,
      paper_id: task.paper_id,
      status: task.status as TaskStatus,
      progress: STATUS_PROGRESS.pending,
      storage_key: task.storage_key,
      error_message: task.error_message,
      attempts: task.attempts,
      created_at: task.created_at,
      updated_at: task.updated_at,
      completed_at: task.completed_at,
    };
  } catch (error) {
    logger.error(`Failed to create task for paper ${paper_id}:`, error);
    throw new Error('Failed to create processing task');
  }
}

/**
 * Update task status and optionally error message
 */
export async function updateTaskStatus(
  taskId: string,
  status: TaskStatus,
  error_message?: string
): Promise<TaskStatusResponse> {
  try {
    const updateData: {
      status: string;
      error_message?: string | null;
      completed_at?: Date | null;
    } = {
      status,
      error_message: error_message || null,
    };

    // Set completedAt when task reaches terminal state
    if (status === 'completed' || status === 'failed') {
      updateData.completed_at = new Date();
    }

    const task = await prisma.processing_tasks.update({
      where: { id: taskId },
      data: updateData,
    });

    logger.info(`Updated task ${taskId} status to ${status}`);

    return {
      taskId: task.id,
      paper_id: task.paper_id,
      status: task.status as TaskStatus,
      progress: getProgressPercent(task.status as TaskStatus),
      storage_key: task.storage_key,
      error_message: task.error_message,
      attempts: task.attempts,
      created_at: task.created_at,
      updated_at: task.updated_at,
      completed_at: task.completed_at,
    };
  } catch (error) {
    logger.error(`Failed to update task ${taskId}:`, error);
    throw new Error('Failed to update task status');
  }
}

/**
 * Get task status by paper ID (for polling)
 */
export async function getTaskStatus(paper_id: string): Promise<TaskStatusResponse | null> {
  try {
    const task = await prisma.processing_tasks.findUnique({
      where: { paper_id: paper_id },
    });

    if (!task) {
      return null;
    }

    return {
      taskId: task.id,
      paper_id: task.paper_id,
      status: task.status as TaskStatus,
      progress: getProgressPercent(task.status as TaskStatus),
      storage_key: task.storage_key,
      error_message: task.error_message,
      attempts: task.attempts,
      created_at: task.created_at,
      updated_at: task.updated_at,
      completed_at: task.completed_at,
    };
  } catch (error) {
    logger.error(`Failed to get task status for paper ${paper_id}:`, error);
    throw new Error('Failed to get task status');
  }
}

/**
 * Get task status by task ID
 */
export async function getTaskById(taskId: string): Promise<TaskStatusResponse | null> {
  try {
    const task = await prisma.processing_tasks.findUnique({
      where: { id: taskId },
    });

    if (!task) {
      return null;
    }

    return {
      taskId: task.id,
      paper_id: task.paper_id,
      status: task.status as TaskStatus,
      progress: getProgressPercent(task.status as TaskStatus),
      storage_key: task.storage_key,
      error_message: task.error_message,
      attempts: task.attempts,
      created_at: task.created_at,
      updated_at: task.updated_at,
      completed_at: task.completed_at,
    };
  } catch (error) {
    logger.error(`Failed to get task ${taskId}:`, error);
    throw new Error('Failed to get task');
  }
}

/**
 * Get progress percentage for a status
 */
export function getProgressPercent(status: TaskStatus): number {
  return STATUS_PROGRESS[status] ?? 0;
}

/**
 * Get all pending tasks (for worker to pick up)
 */
export async function getPendingTasks(limit: number = 10): Promise<TaskStatusResponse[]> {
  try {
    const tasks = await prisma.processing_tasks.findMany({
      where: { status: 'pending' },
      orderBy: { created_at: 'asc' },
      take: limit,
    });

    return tasks.map(task => ({
      taskId: task.id,
      paper_id: task.paper_id,
      status: task.status as TaskStatus,
      progress: STATUS_PROGRESS.pending,
      storage_key: task.storage_key,
      error_message: task.error_message,
      attempts: task.attempts,
      created_at: task.created_at,
      updated_at: task.updated_at,
      completed_at: task.completed_at,
    }));
  } catch (error) {
    logger.error('Failed to get pending tasks:', error);
    throw new Error('Failed to get pending tasks');
  }
}

/**
 * Get tasks by status
 */
export async function getTasksByStatus(
  status: TaskStatus,
  limit: number = 100
): Promise<TaskStatusResponse[]> {
  try {
    const tasks = await prisma.processing_tasks.findMany({
      where: { status },
      orderBy: { created_at: 'asc' },
      take: limit,
    });

    return tasks.map(task => ({
      taskId: task.id,
      paper_id: task.paper_id,
      status: task.status as TaskStatus,
      progress: getProgressPercent(task.status as TaskStatus),
      storage_key: task.storage_key,
      error_message: task.error_message,
      attempts: task.attempts,
      created_at: task.created_at,
      updated_at: task.updated_at,
      completed_at: task.completed_at,
    }));
  } catch (error) {
    logger.error(`Failed to get tasks with status ${status}:`, error);
    throw new Error('Failed to get tasks');
  }
}
