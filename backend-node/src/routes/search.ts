import { Router } from 'express';

const router = Router();

// GET /api/search - 搜索论文
router.get('/', async (req, res, next) => {
  try {
    const { q, source = 'arxiv' } = req.query;

    if (!q) {
      return res.status(400).json({
        success: false,
        error: { message: '搜索关键词不能为空', code: 'MISSING_QUERY' }
      });
    }

    // TODO: 实现多源搜索聚合
    // - arXiv API
    // - Semantic Scholar API
    // - Crossref API

    res.json({
      success: true,
      data: {
        query: q,
        source,
        results: [],
        total: 0
      }
    });
  } catch (error) {
    next(error);
  }
});

// GET /api/search/suggest - 搜索建议
router.get('/suggest', async (req, res, next) => {
  try {
    const { q } = req.query;

    // TODO: 实现搜索建议
    res.json({
      success: true,
      data: {
        query: q,
        suggestions: []
      }
    });
  } catch (error) {
    next(error);
  }
});

export { router as searchRouter };
