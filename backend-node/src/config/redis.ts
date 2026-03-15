import Redis from 'ioredis';
import { logger } from '../utils/logger';

const REDIS_URL = process.env.REDIS_URL || 'redis://localhost:6379/0';

/**
 * Redis client singleton
 * Used for:
 * - Refresh token storage
 * - JWT blacklist (logout)
 * - Rate limiting (future)
 */
export const redisClient = new Redis(REDIS_URL, {
  retryStrategy: (times) => {
    const delay = Math.min(times * 50, 2000);
    return delay;
  },
  maxRetriesPerRequest: 3,
  enableReadyCheck: true,
});

// Connection event handlers
redisClient.on('connect', () => {
  logger.info('Redis client connecting...');
});

redisClient.on('ready', () => {
  logger.info('Redis client connected and ready');
});

redisClient.on('error', (err) => {
  logger.error('Redis client error:', err.message);
});

redisClient.on('reconnecting', () => {
  logger.warn('Redis client reconnecting...');
});

redisClient.on('end', () => {
  logger.warn('Redis client connection closed');
});

/**
 * Check if Redis is connected and ready
 */
export const isRedisReady = (): boolean => {
  return redisClient.status === 'ready';
};

/**
 * Gracefully close Redis connection
 */
export const closeRedisConnection = async (): Promise<void> => {
  await redisClient.quit();
  logger.info('Redis connection closed gracefully');
};
