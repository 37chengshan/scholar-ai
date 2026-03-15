import { Router } from 'express';
import multer from 'multer';
import { v4 as uuidv4 } from 'uuid';
import { logger } from '../utils/logger';
import { authenticate } from '../middleware/auth';
import { requirePermission } from '../middleware/rbac';
import { prisma } from '../config/database';
import { AuthRequest } from '../types/auth';

const router = Router();

// 配置文件上传
const storage = multer.diskStorage({
  destination: (_req, _file, cb) => {
    cb(null, '/tmp/papers');
  },
  filename: (_req, file, cb) => {
    const uniqueName = `${uuidv4()}-${file.originalname}`;
    cb(null, uniqueName);
  }
});

const upload = multer({
  storage,
  limits: {
    fileSize: 50 * 1024 * 1024 // 50MB
  },
  fileFilter: (_req, file, cb) => {
    if (file.mimetype === 'application/pdf' || file.originalname.endsWith('.pdf')) {
      cb(null, true);
    } else {
      cb(new Error('只接受PDF文件'));
    }
  }
});

// Apply authentication to all routes
router.use(authenticate);

// GET /api/papers - 获取论文列表
router.get('/', requirePermission('papers', 'read'), async (req: AuthRequest, res, next) => {
  try {
    // 从查询参数解析分页参数，使用默认值
    const page = Math.max(1, parseInt(req.query.page as string, 10) || 1);
    const limit = Math.min(100, Math.max(1, parseInt(req.query.limit as string, 10) || 20));
    const skip = (page - 1) * limit;

    // 获取当前用户ID（可选，用于过滤用户自己的论文）
    const userId = req.user?.sub;

    // 查询数据库获取论文列表
    const where = userId ? { userId } : {};

    const [papers, total] = await Promise.all([
      prisma.paper.findMany({
        where,
        skip,
        take: limit,
        orderBy: { createdAt: 'desc' },
        select: {
          id: true,
          title: true,
          authors: true,
          year: true,
          abstract: true,
          doi: true,
          arxivId: true,
          status: true,
          keywords: true,
          venue: true,
          citations: true,
          fileSize: true,
          pageCount: true,
          createdAt: true,
          updatedAt: true,
          userId: true
        }
      }),
      prisma.paper.count({ where })
    ]);

    const totalPages = Math.ceil(total / limit);

    res.json({
      success: true,
      data: {
        papers,
        total,
        page,
        limit,
        totalPages
      }
    });
  } catch (error) {
    next(error);
  }
});

// POST /api/papers - 上传论文
router.post('/', requirePermission('papers', 'create'), upload.single('pdf'), async (req, res, next) => {
  try {
    if (!req.file) {
      return res.status(400).json({
        success: false,
        error: { message: '请上传PDF文件', code: 'MISSING_FILE' }
      });
    }

    logger.info(`PDF uploaded: ${req.file.originalname}`);

    // TODO: 调用AI服务解析PDF
    // const aiServiceUrl = process.env.AI_SERVICE_URL;
    // await fetch(`${aiServiceUrl}/parse-pdf`, ...);

    res.status(201).json({
      success: true,
      data: {
        id: uuidv4(),
        filename: req.file.originalname,
        status: 'processing',
        message: 'PDF上传成功，正在解析中...'
      }
    });
  } catch (error) {
    next(error);
  }
});

// GET /api/papers/:id - 获取论文详情
router.get('/:id', requirePermission('papers', 'read'), async (req, res, next) => {
  try {
    const { id } = req.params;
    // TODO: 实现获取论文详情
    res.json({
      success: true,
      data: {
        id,
        status: 'pending'
      }
    });
  } catch (error) {
    next(error);
  }
});

// GET /api/papers/:id/summary - 获取论文精读笔记
router.get('/:id/summary', requirePermission('papers', 'read'), async (req, res, next) => {
  try {
    const { id } = req.params;
    // TODO: 调用AI服务生成精读笔记
    res.json({
      success: true,
      data: {
        paperId: id,
        summary: null,
        status: 'pending'
      }
    });
  } catch (error) {
    next(error);
  }
});

// DELETE /api/papers/:id - 删除论文
router.delete('/:id', requirePermission('papers', 'delete'), async (req, res, next) => {
  try {
    const { id } = req.params;
    // TODO: 实现删除论文
    res.json({
      success: true,
      data: { id, deleted: true }
    });
  } catch (error) {
    next(error);
  }
});

export { router as papersRouter };
