import express, { RequestHandler } from 'express';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';
import cookieParser from 'cookie-parser';
import dotenv from 'dotenv';

import { errorHandler } from './middleware/errorHandler';
import { logger } from './utils/logger';

// 路由
import { papersRouter } from './routes/papers';
import { queriesRouter } from './routes/queries';
import { usersRouter } from './routes/users';
import { searchRouter } from './routes/search';
import { healthRouter } from './routes/health';
import { authRouter } from './routes/auth';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 4000;

// 中间件
app.use(helmet());
app.use(cors({
  origin: process.env.FRONTEND_URL || 'http://localhost:3000',
  credentials: true
}));
app.use(cookieParser() as unknown as express.RequestHandler);
app.use(morgan('combined', { stream: { write: (msg) => logger.info(msg.trim()) } }));
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// 路由
app.use('/api/health', healthRouter);
app.use('/api/auth', authRouter);
app.use('/api/papers', papersRouter);
app.use('/api/queries', queriesRouter);
app.use('/api/users', usersRouter);
app.use('/api/search', searchRouter);

// 错误处理
app.use(errorHandler);

// 启动服务器（仅在非测试环境或明确请求时）
if (process.env.NODE_ENV !== 'test' || process.env.START_SERVER === 'true') {
  app.listen(PORT, () => {
    logger.info(`🚀 ScholarAI API server running on port ${PORT}`);
    logger.info(`📚 Environment: ${process.env.NODE_ENV || 'development'}`);
    logger.info(`🔗 AI Service URL: ${process.env.AI_SERVICE_URL || 'http://localhost:8000'}`);
  });
}

export default app;
