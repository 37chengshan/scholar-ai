# ScholarAI 测试总览

## 测试架构

ScholarAI 智读系统包含完整的测试套件，涵盖单元测试、集成测试和端到端（E2E）测试。

### 测试目录结构

```
backend-node/tests/
├── e2e/                          # 端到端测试
│   ├── comprehensive-integration.e2e.test.ts  # ⭐ 新增：综合集成测试
│   ├── auth.e2e.test.ts          # 认证测试
│   ├── papers.e2e.test.ts        # 论文上传测试
│   ├── pdf-upload-workflow.e2e.test.ts  # PDF上传流程测试
│   ├── chat-with-arxiv.e2e.test.ts  # Chat对话测试
│   ├── queries.e2e.test.ts       # RAG查询测试
│   ├── graph.e2e.test.ts         # 知识图谱测试
│   ├── rbac.e2e.test.ts          # 权限控制测试
│   ├── health.e2e.test.ts        # 健康检查测试
│   └── COMPREHENSIVE-TEST-README.md  # ⭐ 新增：测试指南
│
├── unit/                         # 单元测试
│   ├── papers.starred.test.ts    # 收藏功能测试
│   ├── retry.test.ts             # 重试逻辑测试
│   └── transaction.test.ts       # 事务处理测试
│
├── helpers/                      # 测试辅助工具
│   ├── db.ts                     # 数据库辅助函数
│   ├── server.ts                 # 服务器辅助函数
│   └── auth.ts                   # 认证辅助函数
│
└── TEST-OVERVIEW.md              # ⭐ 新增：测试总览文档
```

## 测试类型

### 1. 综合集成测试 ⭐ NEW

**文件**: `comprehensive-integration.e2e.test.ts`

**功能覆盖**:
- ✅ 智能注册（检测已存在账户）
- ✅ 登录认证
- ✅ 真实PDF上传解析（实时监控）
- ✅ 文献库管理（列表、详情、删除）
- ✅ 笔记生成与编辑
- ✅ Chat对话（阻塞式、流式、多论文）
- ✅ 外部搜索（arXiv、Semantic Scholar）

**运行方式**:
```bash
npm run test:comprehensive
```

**特点**:
- 使用固定测试账户（避免重复注册）
- 真实PDF文件测试（270KB - 5.5MB）
- 实时进度监控（每5秒轮询）
- 完整的用户旅程测试
- 详细的测试报告输出

### 2. 认证测试

**文件**: `auth.e2e.test.ts`

**测试内容**:
- 用户注册（邮箱验证、密码强度）
- 用户登录（Cookie设置、JWT Token）
- Token刷新
- 用户信息获取
- 登出功能

**运行方式**:
```bash
npm test tests/e2e/auth.e2e.test.ts
```

### 3. 论文上传测试

**文件**: `papers.e2e.test.ts` 和 `pdf-upload-workflow.e2e.test.ts`

**测试内容**:
- 上传URL生成
- PDF文件上传
- Webhook回调处理
- 状态轮询
- 文件验证
- 权限控制

**运行方式**:
```bash
npm run test:pdf
```

### 4. Chat对话测试

**文件**: `chat-with-arxiv.e2e.test.ts`

**测试内容**:
- arXiv论文下载
- 多论文上传
- RAG查询
- 多论文对比
- 查询历史记录

**运行方式**:
```bash
npm run test:chat
```

### 5. RAG查询测试

**文件**: `queries.e2e.test.ts`

**测试内容**:
- 单论文查询
- 多论文查询
- 查询历史
- 查询删除
- 并发查询测试

**运行方式**:
```bash
npm test tests/e2e/queries.e2e.test.ts
```

### 6. 其他测试

- **知识图谱测试** (`graph.e2e.test.ts`): Neo4j集成测试
- **权限控制测试** (`rbac.e2e.test.ts`): RBAC功能测试
- **健康检查测试** (`health.e2e.test.ts`): 服务状态测试
- **外部添加测试** (`test_external_add.e2e.test.ts`): 外部论文添加测试

## 测试辅助工具

### 1. 数据库辅助 (`helpers/db.ts`)

```typescript
// 清理测试数据
await cleanupTestData();

// 生成测试用户数据
const userData = generateTestUserData();

// 关闭数据库连接
await closeDatabaseConnections();
```

### 2. 服务器辅助 (`helpers/server.ts`)

```typescript
// 创建测试Agent
const agent = createTestAgent();

// 创建已认证用户
const { agent, user } = await createAuthenticatedUser('user');

// 创建管理员用户
const { agent, user } = await createAuthenticatedUser('admin');
```

### 3. 认证辅助 (`helpers/auth.ts`)

```typescript
// 生成测试AccessToken
const token = generateTestAccessToken(userId);
```

## 运行所有测试

### 方式1: 运行所有E2E测试

```bash
npm test tests/e2e/
```

### 方式2: 运行所有单元测试

```bash
npm test tests/unit/
```

### 方式3: 运行全部测试

```bash
npm test
```

### 方式4: 生成覆盖率报告

```bash
npm run test:coverage
```

### 方式5: 监听模式

```bash
npm run test:watch
```

## 测试配置

### Jest配置

配置文件: `jest.config.js`

```javascript
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  roots: ['<rootDir>/tests'],
  testMatch: ['**/*.test.ts'],
  collectCoverageFrom: [
    'src/**/*.ts',
    '!src/**/*.d.ts',
  ],
  coverageThreshold: {
    global: {
      branches: 50,
      functions: 50,
      lines: 50,
      statements: 50,
    },
  },
};
```

### 环境变量

测试需要以下环境变量：

```bash
DATABASE_URL=postgresql://postgres:password@localhost:5432/scholarai_test
REDIS_URL=redis://localhost:6379
NEO4J_URI=bolt://localhost:7687
JWT_SECRET=test-secret-key
AI_SERVICE_URL=http://localhost:8000
```

## 测试数据管理

### 测试账户

综合测试使用固定账户：
- Email: `integration-test@example.com`
- Password: `TestIntegration123!`

其他测试使用随机账户（自动生成）：
```typescript
const userData = generateTestUserData();
// Email: test-{timestamp}-{randomId}@example.com
```

### 清理策略

测试结束后自动清理：
1. 删除所有 `@example.com` 邵箱的用户
2. 删除关联的论文、笔记、查询记录
3. 清理过期的Refresh Token
4. 清理Redis缓存

### 测试PDF文件

位置: `/Users/cc/scholar-ai-deploy/schlar ai/doc/测试论文/`

包含文件:
- `2604.01245v1.pdf` (270KB)
- `2604.01226v1.pdf` (5.5MB)
- 以及其他多个PDF文件

## 性能基准

### 测试执行时间

| 测试类型 | 平均耗时 | 最大超时 |
|---------|---------|---------|
| 认证测试 | 5秒 | 10秒 |
| 论文上传 | 10秒 | 60秒 |
| PDF解析监控 | 5-10分钟 | 600秒 |
| Chat对话 | 30秒 | 120秒 |
| 外部搜索 | 10秒 | 30秒 |
| 综合测试 | 15-20分钟 | 600秒 |

### PDF解析性能

- 小文件（<1MB）: ~30-60秒
- 中等文件（1-5MB）: ~2-5分钟
- 大文件（>5MB）: ~5-10分钟

### API响应时间

- 认证API: <100ms
- 论文列表API: <200ms
- Chat API: 1-30秒（取决于LLM）
- 搜索API: 1-5秒

## CI/CD集成

### GitHub Actions配置

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
      redis:
        image: redis:7
    
    steps:
      - uses: actions/checkout@v3
      - name: Install dependencies
        run: npm ci
      - name: Run tests
        run: npm test
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## 测试最佳实践

### 1. 使用Agent管理Cookie

```typescript
const agent = request.agent(app);

// 注册
await agent.post('/api/auth/register').send(userData);

// 登录（Cookie自动保存）
await agent.post('/api/auth/login').send({ email, password });

// 后续请求自动携带Cookie
await agent.get('/api/papers');
```

### 2. 异步操作处理

```typescript
// 使用async/await
const response = await agent.get('/api/papers');

// 并发测试
const promises = Array.from({ length: 5 }, (_, i) => 
  agent.post('/api/chat').send({ message: `test-${i}` })
);
await Promise.all(promises);
```

### 3. 错误处理

```typescript
try {
  const response = await agent.get('/api/papers');
  expect(response.status).toBe(200);
} catch (error) {
  console.error('Test failed:', error);
  throw error;
}
```

### 4. 状态共享

```typescript
// 在beforeAll中初始化共享状态
let paperId: string;

beforeAll(async () => {
  const response = await agent.post('/api/papers').send({ filename: 'test.pdf' });
  paperId = response.body.data.paperId;
});

// 在测试中使用
it('should get paper details', async () => {
  const response = await agent.get(`/api/papers/${paperId}`);
  expect(response.status).toBe(200);
});
```

### 5. 清理资源

```typescript
afterAll(async () => {
  await cleanupTestData();
  await closeDatabaseConnections();
});
```

## 调试技巧

### 1. 单步调试

```bash
jest tests/e2e/comprehensive-integration.e2e.test.ts --bail=1 --verbose
```

### 2. 检查数据库

```bash
psql -U postgres -d scholarai

-- 查看测试数据
SELECT * FROM users WHERE email LIKE '%example.com';
SELECT * FROM papers WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%example.com');
```

### 3. 日志输出

```typescript
console.log('Request:', requestBody);
console.log('Response:', response.body);
```

### 4. 检查服务状态

```bash
curl http://localhost:4000/health
curl http://localhost:8000/health
```

## 测试报告

### 综合测试报告输出

```
========================================
综合集成测试总结报告
========================================

用户账户:
  邮箱: integration-test@example.com
  用户ID: uuid-xxxxx
  状态: ✓ 已认证

PDF上传与解析:
  总上传: 2 个论文
  成功解析: 2 个论文
  ✓ 2604.01245v1.pdf: completed
  ✓ 2604.01226v1.pdf: completed

文献库管理:
  ✓ 列表查询成功
  ✓ 详情查询成功
  ✓ 删除功能正常

笔记功能:
  ✓ 笔记生成测试完成
  ✓ 笔记获取测试完成
  ✓ 笔记导出测试完成

Chat对话:
  ✓ 阻塞式对话（单论文）测试完成
  ✓ 阻塞式对话（多论文）测试完成
  ✓ 流式对话（SSE）测试完成

外部搜索:
  ✓ arXiv搜索成功
  ✓ Semantic Scholar搜索成功
  ✓ 统一搜索成功
  ✓ 外部论文添加成功

========================================
测试完成时间: 2026-04-05T...
========================================
```

## 相关文档

- [综合测试指南](./e2e/COMPREHENSIVE-TEST-README.md)
- [API文档](../../doc/swagger.json)
- [架构文档](../../doc/架构/系统架构图.md)
- [开发文档](../../CLAUDE.md)

## 快速开始

```bash
# 1. 确保服务运行
docker-compose up -d postgres redis neo4j
cd backend-python && python -m uvicorn app.main:app --reload --port 8000
cd backend-node && npm run dev

# 2. 运行综合测试
npm run test:comprehensive

# 3. 查看测试报告
# 测试输出会显示在终端中
```

## 支持

如有问题，请：
1. 检查测试日志
2. 查看服务日志：`backend-node/logs/` 和 `backend-python/logs/`
3. 检查数据库状态
4. 参考 [COMPREHENSIVE-TEST-README.md](./e2e/COMPREHENSIVE-TEST-README.md)

---

最后更新: 2026-04-05