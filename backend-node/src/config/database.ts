import { PrismaClient } from '@prisma/client';

// PrismaClient is attached to the `global` object in development to prevent
// exhausting your database connection limit.
// Learn more: https://pris.ly/d/help/next-js-best-practices

declare global {
  // eslint-disable-next-line no-var
  var prisma: PrismaClient | undefined;
}

const prismaOptions = {
  log: process.env.NODE_ENV === 'development'
    ? (['query', 'info', 'warn', 'error'] as const)
    : (['error'] as const),
};

// Create singleton Prisma client
const prisma = global.prisma || new PrismaClient({
  log: process.env.NODE_ENV === 'development'
    ? (['query', 'info', 'warn', 'error'] as const)
    : (['error'] as const),
});

// Store in global for hot-reloading in development
if (process.env.NODE_ENV !== 'production') {
  global.prisma = prisma;
}

// Connection error handling
prisma.$connect()
  .then(() => {
    console.log('[Database] Connected successfully');
  })
  .catch((error: Error) => {
    console.error('[Database] Connection failed:', error);
    // Don't exit - let the application handle reconnection or failure
  });

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

export { prisma };
export default prisma;
