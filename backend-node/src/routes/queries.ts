import { Router } from 'express';
import { authenticate } from '../middleware/auth';
import { requirePermission } from '../middleware/rbac';

const router = Router();

// Apply authentication to all routes
router.use(authenticate);

// POST /api/queries - 提交查询（RAG问答）
router.post('/', requirePermission('queries', 'create'), async (req, res, next) => {
  try {
    const { question, paperIds, queryType = 'single' } = req.body;

    if (!question) {
      return res.status(400).json({
        success: false,
        error: { message: '问题不能为空', code: 'MISSING_QUESTION' }
      });
    }

    // TODO: 调用AI服务进行RAG问答
    // const aiServiceUrl = process.env.AI_SERVICE_URL;
    // const response = await fetch(`${aiServiceUrl}/rag-query`, ...);

    res.json({
      success: true,
      data: {
        id: 'query-1',
        question,
        answer: null,
        status: 'processing',
        sources: []
      }
    });
  } catch (error) {
    next(error);
  }
});

// GET /api/queries - 获取查询历史
router.get('/', requirePermission('queries', 'read'), async (_req, res, next) => {
  try {
    // TODO: 实现获取查询历史
    res.json({
      success: true,
      data: {
        queries: [],
        total: 0
      }
    });
  } catch (error) {
    next(error);
  }
});

// GET /api/queries/:id - 获取查询详情
router.get('/:id', requirePermission('queries', 'read'), async (req, res, next) => {
  try {
    const { id } = req.params;
    // TODO: 实现获取查询详情
    res.json({
      success: true,
      data: {
        id,
        question: '',
        answer: '',
        status: 'completed'
      }
    });
  } catch (error) {
    next(error);
  }
});

export { router as queriesRouter };
