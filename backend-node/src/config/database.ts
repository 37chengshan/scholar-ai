import { PrismaClient } from '@prisma/client';

// PrismaClient is attached to the `global` object in development to prevent
// exhausting your database connection limit.
// Learn more: https://pris.ly/d/help/next-js-best-practices

declare global {
  // eslint-disable-next-line no-var
  var prisma: PrismaClient | undefined;
}

// 获取或创建 PrismaClient 的函数
function getPrismaClient(): PrismaClient {
  // 检查全局实例
  if (global.prisma) {
    return global.prisma;
  }

  // 创建新实例
  const client = new PrismaClient({
    log: process.env.NODE_ENV === 'development'
      ? (['query', 'info', 'warn', 'error'] as const)
      : (['error'] as const),
  });

  // Store in global for hot-reloading in development
  if (process.env.NODE_ENV !== 'production') {
    global.prisma = client;
  }

  // Connection error handling
  client.$connect()
    .then(() => {
      console.log('[Database] Connected successfully');
    })
    .catch((error: Error) => {
      console.error('[Database] Connection failed:', error);
    });

  return client;
}

// 导出 prisma 实例（延迟初始化）
export const prisma = getPrismaClient();

// Graceful shutdown handler
const gracefulShutdown = async (signal: string): Promise<void> => {
  console.log(`[Database] Received ${signal}, disconnecting...`);
  await prisma.$disconnect();
  console.log('[Database] Disconnected successfully');
  process.exit(0);
};

// Register shutdown handlers
process.on('SIGINT', () => gracefulShutdown('SIGINT'));
process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));

export default prisma;
