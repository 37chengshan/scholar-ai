import { Router } from 'express';
import { v4 as uuidv4 } from 'uuid';
import { prisma } from '../config/database';
import { redisClient } from '../config/redis';
import { logger } from '../utils/logger';
import { ErrorTypes } from '../types/auth';

const router = Router();

/**
 * GET /api/system/storage
 * Returns storage usage metrics
 */
router.get('/storage', async (req, res, next) => {
  try {
    // Get paper count and file storage estimation
    const papers = await prisma.papers.count();
    const avgFileSize = 2 * 1024 * 1024; // 2MB average per paper
    const estimatedFileStorage = papers * avgFileSize;

    // Convert to GB
    const usedFileStorageGB = (estimatedFileStorage / (1024 * 1024 * 1024)).toFixed(1);
    const totalFileStorageGB = 50; // 50GB limit
    const fileStoragePercentage = Math.round((estimatedFileStorage / (totalFileStorageGB * 1024 * 1024 * 1024)) * 100);

    // Mock vector DB stats (would need Milvus client integration)
    const vectorDB = {
      used: '1.2',
      total: '5',
      percentage: 24,
    };

    const fileStorage = {
      used: usedFileStorageGB,
      total: totalFileStorageGB.toString(),
      percentage: fileStoragePercentage,
    };

    res.json({
      success: true,
      data: {
        vectorDB,
        fileStorage,
      },
    });
  } catch (error) {
    next(error);
  }
});

/**
 * GET /api/system/logs/stream
 * SSE endpoint for streaming system logs
 */
router.get('/logs/stream', (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');

  // Send heartbeat every 15 seconds
  const heartbeatInterval = setInterval(() => {
    res.write(': heartbeat\n\n');
  }, 15000);

  // Send mock system logs
  const logInterval = setInterval(() => {
    const logs = [
      { level: 'INFO', message: 'User session authenticated' },
      { level: 'INFO', message: 'API rate limit normal' },
      { level: 'INFO', message: 'Ingestion batch completed' },
      { level: 'WARN', message: 'API rate limit approaching' },
      { level: 'WARN', message: 'Storage usage >80%' },
      { level: 'ERROR', message: 'API request failed' },
      { level: 'ERROR', message: 'Database connection timeout' },
    ];

    const randomLog = logs[Math.floor(Math.random() * logs.length)];
    const logEntry = {
      level: randomLog.level,
      message: randomLog.message,
      timestamp: new Date().toISOString(),
    };

    res.write(`data: ${JSON.stringify(logEntry)}\n\n`);
  }, 3000); // Send log every 3 seconds

  // Clean up on client disconnect
  req.on('close', () => {
    clearInterval(heartbeatInterval);
    clearInterval(logInterval);
  });
});

export { router as systemRouter };