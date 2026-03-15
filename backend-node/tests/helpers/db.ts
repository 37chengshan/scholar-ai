import { prisma } from '../../src/config/database';
import { redisClient } from '../../src/config/redis';

/**
 * Clean up test data from database
 */
export async function cleanupTestData(): Promise<void> {
  try {
    // Delete test users (with test- prefix or @example.com domain)
    await prisma.user.deleteMany({
      where: {
        OR: [
          { email: { contains: 'test-' } },
          { email: { endsWith: '@example.com' } },
        ],
      },
    });

    // Clean up any remaining test refresh tokens
    await prisma.refreshToken.deleteMany({
      where: {
        expiresAt: { lt: new Date() },
      },
    });
  } catch (error) {
    console.error('Cleanup error:', error);
  }
}

/**
 * Clean up Redis test data
 */
export async function cleanupRedisTestData(): Promise<void> {
  try {
    // Get all keys matching refresh:* and blacklist:* patterns
    const refreshKeys = await redisClient.keys('refresh:*');
    const blacklistKeys = await redisClient.keys('blacklist:*');

    if (refreshKeys.length > 0) {
      await redisClient.del(...refreshKeys);
    }
    if (blacklistKeys.length > 0) {
      await redisClient.del(...blacklistKeys);
    }
  } catch (error) {
    console.error('Redis cleanup error:', error);
  }
}

/**
 * Generate unique test user data
 */
export function generateTestUserData() {
  const timestamp = Date.now();
  const randomId = Math.random().toString(36).substring(2, 8);
  return {
    email: `test-${timestamp}-${randomId}@example.com`,
    password: 'Test123!',
    name: `Test User ${randomId}`,
  };
}

/**
 * Close database connections
 */
export async function closeDatabaseConnections(): Promise<void> {
  await prisma.$disconnect();
  await redisClient.quit();
}
