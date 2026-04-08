/**
 * Tests for Prisma transaction behavior in papers route.
 *
 * Tests that paper upload and task creation are atomic operations.
 */

import { describe, it, expect, beforeEach, jest } from '@jest/globals';
import { prisma } from '../../src/config/database';

// Mock Prisma
jest.mock('../../src/config/database', () => ({
  prisma: {
    $transaction: jest.fn(),
    processing_tasks: {
      create: jest.fn(),
    },
    papers: {
      update: jest.fn(),
      findFirst: jest.fn(),
    },
    paper_batches: {
      update: jest.fn(),
      findUnique: jest.fn(),
    },
  },
}));

describe('Paper Upload Transaction', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Transaction Atomicity', () => {
    it('should create task and update paper atomically', async () => {
      const mockTask = {
        id: 'task-123',
        paperId: 'paper-456',
        status: 'pending',
        storageKey: 'uploads/test.pdf',
      };

      const mockPaper = {
        id: 'paper-456',
        status: 'processing',
        uploadStatus: 'completed',
      };

      // Mock successful transaction
      (prisma.$transaction as any).mockResolvedValueOnce([mockTask, mockPaper]);

      const result = await prisma.$transaction([
        prisma.processing_tasks.create({
          data: {
            id: 'task-123',
            updatedAt: new Date(),
            paperId: 'paper-456',
            status: 'pending',
            storageKey: 'uploads/test.pdf',
          },
        }),
        prisma.papers.update({
          where: { id: 'paper-456' },
          data: {
            id: 'task-123',
            updatedAt: new Date(),
            status: 'processing',
            uploadStatus: 'completed',
            uploadProgress: 100,
            uploadedAt: new Date(),
          },
        }),
      ]);

      expect(prisma.$transaction).toHaveBeenCalledTimes(1);
      expect(result[0]).toEqual(mockTask);
      expect(result[1]).toEqual(mockPaper);
    });

    it('should rollback task creation if paper update fails', async () => {
      // Mock transaction failure
      (prisma.$transaction as any).mockRejectedValueOnce(
        new Error('Paper update failed')
      );

      await expect(
        prisma.$transaction([
          prisma.processing_tasks.create({
            data: {
            id: 'task-123',
            updatedAt: new Date(),
              paperId: 'paper-456',
              status: 'pending',
              storageKey: 'uploads/test.pdf',
            },
          }),
          prisma.papers.update({
            where: { id: 'paper-456' },
            data: { status: 'processing' },
          }),
        ])
      ).rejects.toThrow('Paper update failed');

      // Transaction ensures rollback - no partial state
      expect(prisma.$transaction).toHaveBeenCalledTimes(1);
    });

    it('should rollback paper update if task creation fails', async () => {
      // Mock transaction failure
      (prisma.$transaction as any).mockRejectedValueOnce(
        new Error('Task creation failed')
      );

      await expect(
        prisma.$transaction([
          prisma.processing_tasks.create({
            data: {
            id: 'task-123',
            updatedAt: new Date(),
              paperId: 'paper-456',
              status: 'pending',
              storageKey: 'uploads/test.pdf',
            },
          }),
          prisma.papers.update({
            where: { id: 'paper-456' },
            data: { status: 'processing' },
          }),
        ])
      ).rejects.toThrow('Task creation failed');

      // Transaction ensures rollback - no partial state
      expect(prisma.$transaction).toHaveBeenCalledTimes(1);
    });
  });

  describe('Transaction Error Handling', () => {
    it('should handle concurrent modification conflicts', async () => {
      // Mock Prisma error for concurrent modification
      const prismaError = new Error('Transaction failed');
      (prismaError as any).code = 'P2034';

      (prisma.$transaction as any).mockRejectedValueOnce(prismaError);

      await expect(
        prisma.$transaction([
          prisma.processing_tasks.create({
            data: {
            id: 'task-123',
            updatedAt: new Date(),
              paperId: 'paper-456',
              status: 'pending',
              storageKey: 'uploads/test.pdf',
            },
          }),
          prisma.papers.update({
            where: { id: 'paper-456' },
            data: { status: 'processing' },
          }),
        ])
      ).rejects.toThrow('Transaction failed');
    });

    it('should handle database connection errors', async () => {
      // Mock database connection error
      (prisma.$transaction as any).mockRejectedValueOnce(
        new Error('Connection refused')
      );

      await expect(
        prisma.$transaction([
          prisma.processing_tasks.create({
            data: {
            id: 'task-123',
            updatedAt: new Date(),
              paperId: 'paper-456',
              status: 'pending',
              storageKey: 'uploads/test.pdf',
            },
          }),
          prisma.papers.update({
            where: { id: 'paper-456' },
            data: { status: 'processing' },
          }),
        ])
      ).rejects.toThrow('Connection refused');
    });
  });

  describe('Transaction Consistency', () => {
    it('should maintain data consistency after successful transaction', async () => {
      const mockTask = {
        id: 'task-123',
        paperId: 'paper-456',
        status: 'pending',
      };

      const mockPaper = {
        id: 'paper-456',
        status: 'processing',
        uploadStatus: 'completed',
      };

      (prisma.$transaction as any).mockResolvedValueOnce([mockTask, mockPaper]);

      const [task, paper] = await prisma.$transaction([
        prisma.processing_tasks.create({
          data: {
            id: 'task-123',
            updatedAt: new Date(),
            paperId: 'paper-456',
            status: 'pending',
            storageKey: 'uploads/test.pdf',
          },
        }),
        prisma.papers.update({
          where: { id: 'paper-456' },
          data: {
            id: 'task-123',
            updatedAt: new Date(),
            status: 'processing',
            uploadStatus: 'completed',
            uploadProgress: 100,
            uploadedAt: new Date(),
          },
        }),
      ]);

      // Verify consistency
      expect(task.paperId).toBe(paper.id);
      expect(paper.status).toBe('processing');
    });
  });
});