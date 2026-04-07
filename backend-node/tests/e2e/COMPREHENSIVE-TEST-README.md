# 综合集成测试指南

## 测试概述

这个综合集成测试脚本覆盖了 ScholarAI 智读系统的所有核心功能模块，提供了一个完整的用户旅程测试。

### 测试内容

1. **智能注册与登录**
   - 检测已存在账户，避免重复注册
   - 使用固定测试账户：`integration-test@example.com`
   - JWT认证和Cookie管理

2. **真实PDF上传与解析（完整流水线）**
   - 使用真实PDF文件（来自 `doc/测试论文/` 目录）
   - **实时监控8个处理阶段**:
     * pending (等待处理)
     * processing_ocr (OCR识别)
     * parsing (PDF结构解析)
     * extracting_imrad (提取IMRaD结构)
     * generating_notes (生成阅读笔记)
     * storing_vectors (存储向量嵌入) ⭐
     * indexing_multimodal (多模态索引) ⭐
     * completed (完成)
   - **向量嵌入验证**:
     * 文本向量（Qwen3-VL 2048维）
     * 图片向量（多模态嵌入）
     * 表格向量（多模态嵌入）
   - **存储验证**:
     * Milvus向量数据库
     * 多模态索引完整性
   - 支持不同大小的PDF文件（270KB到5.5MB）

3. **文献库管理**
   - 论文列表查询（分页、筛选）
   - 论文详情获取
   - 论文删除功能
   - 授权验证

4. **笔记生成与编辑**
   - 自动笔记生成
   - 笔记获取和查看
   - 笔记重新生成（修改请求）
   - Markdown导出

5. **Chat对话测试**
   - 阻塞式对话（单论文）
   - 阻塞式对话（多论文对比）
   - 流式对话（SSE实时流）
   - 会话确认（危险操作）

6. **外部搜索**
   - arXiv论文搜索
   - Semantic Scholar论文搜索
   - 统一搜索（多源聚合）
   - 外部论文添加到文献库
   - 重复添加保护

## 前置条件

### 1. 环境准备

确保以下服务正在运行：

```bash
# PostgreSQL + PGVector
docker-compose up -d postgres

# Neo4j
docker-compose up -d neo4j

# Redis
docker-compose up -d redis

# Python AI Service (Port 8000)
cd backend-python
python -m uvicorn app.main:app --reload --port 8000

# Node.js API Gateway (Port 4000)
cd backend-node
npm run dev
```

### 2. 测试PDF文件

测试使用真实的PDF文件，位于：
```
/Users/cc/scholar-ai-deploy/schlar ai/doc/测试论文/
``

包含的测试文件：
- `2604.01245v1.pdf` (270KB) - 小文件，快速测试
- `2604.01226v1.pdf` (5.5MB) - 大文件，压力测试

### 3. 数据库清理

测试脚本会自动清理测试数据（包含 `@example.com` 的用户），但建议在首次运行前手动清理：

```bash
cd backend-node
npm run db:migrate
```

## 运行测试

### 方式1: 使用 Jest 运行（推荐）

```bash
cd backend-node

# 运行综合测试
npm test tests/e2e/comprehensive-integration.e2e.test.ts

# 或者使用自定义脚本
npm run test:comprehensive
```

### 方式2: 直接使用 Jest CLI

```bash
cd backend-node

# 运行单个测试文件
jest tests/e2e/comprehensive-integration.e2e.test.ts --verbose --detectOpenHandles

# 运行并输出详细日志
jest tests/e2e/comprehensive-integration.e2e.test.ts --verbose --no-cache --runInBand

# 调试模式（停止在第一个失败）
jest tests/e2e/comprehensive-integration.e2e.test.ts --bail=1
```

### 方式3: 监听模式

```bash
cd backend-node
jest tests/e2e/comprehensive-integration.e2e.test.ts --watch
```

## 测试配置

### 自定义配置

测试配置在 `comprehensive-integration.e2e.test.ts` 的 `testConfig` 对象中：

```typescript
const testConfig = {
  testEmail: 'integration-test@example.com',
  testPassword: 'TestIntegration123!',
  testName: 'Integration Test User',
  testPapers: [
    '2604.01245v1.pdf',   // Small paper
    '2604.01226v1.pdf',   // Large paper
  ],
  maxPollAttempts: 120,   // 最大轮询次数
  pollDelayMs: 5000,      // 轮询间隔（毫秒）
};
```

### 调整超时时间

PDF解析可能需要较长时间，测试设置了以下超时：

- **上传测试**: 60秒
- **轮询等待**: 600秒（10分钟）
- **Chat测试**: 120秒
- **搜索测试**: 30秒

如果解析速度较慢，可以调整 `maxPollAttempts` 和 `pollDelayMs`。

## 测试输出

测试会输出详细的进度信息：

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

## 常见问题

### 1. 测试失败：连接超时

**原因**: 后端服务未启动或端口不正确

**解决方案**:
```bash
# 检查服务状态
curl http://localhost:4000/health
curl http://localhost:8000/health

# 如果使用不同端口，修改环境变量
export PORT=4000
export AI_SERVICE_URL=http://localhost:8000
```

### 2. 测试失败：PDF文件不存在

**原因**: 测试PDF目录路径不正确

**解决方案**:
检查 `testPdfDir` 路径是否正确：
```typescript
const testPdfDir = '/Users/cc/scholar-ai-deploy/schlar ai/doc/测试论文';
```

或者修改为你的实际路径。

### 3. 测试失败：解析超时

**原因**: Python服务处理速度慢或LLM API响应慢

**解决方案**:
1. 检查Python服务日志：`tail -f backend-python/logs/app.log`
2. 增加超时时间：`maxPollAttempts: 200`
3. 减少轮询间隔：`pollDelayMs: 3000`

### 4. 测试失败：数据库连接错误

**原因**: PostgreSQL或Redis未运行

**解决方案**:
```bash
# 启动数据库
docker-compose up -d postgres redis neo4j

# 检查连接
docker ps
docker logs scholarai-postgres
```

### 5. 测试失败：认证无效

**原因**: JWT密钥不匹配或Token过期

**解决方案**:
检查 `.env` 文件：
```bash
JWT_SECRET=your-secret-key
JWT_EXPIRES_IN=15m
REFRESH_TOKEN_EXPIRES_IN=7d
```

## 性能监控

### 测试执行时间统计

测试完成后，可以查看各阶段耗时：

```bash
# Jest输出包含时间统计
jest tests/e2e/comprehensive-integration.e2e.test.ts --verbose
```

### PDF解析性能

监控Python服务的处理时间：

```python
# 在 backend-python/app/core/processor.py 中
logger.info(f"PDF processed in {duration}ms")
```

**各阶段耗时参考**:
- OCR识别: 2-10秒
- PDF解析: 5-15秒
- IMRaD提取: 2-5秒
- 笔记生成: 5-15秒
- **向量嵌入**: 5-20秒 ⭐
- **多模态索引**: 10-30秒 ⭐

总计: 小文件（270KB）约21秒，大文件（5MB）约60秒

### API响应时间

Node.js服务会记录每个请求的耗时：

```typescript
// backend-node/src/utils/logger.ts
logger.info(`API Response time: ${responseTime}ms`);
```

## 扩展测试

### 添加更多测试PDF

修改 `testPapers` 数组：

```typescript
testPapers: [
  '2604.01245v1.pdf',
  '2604.01226v1.pdf',
  '2604.01228v1.pdf',  // 添加更多
],
```

### 测试不同场景

1. **并发上传测试**:
```typescript
// 在 Step 2 中添加并发上传测试
for (const file of testPapers) {
  await Promise.all([
    uploadPaper(file),
    uploadPaper(file),
  ]);
}
```

2. **大批量搜索测试**:
```typescript
// 在 Step 6 中添加批量搜索
for (let i = 0; i < 10; i++) {
  await searchArxiv(`query-${i}`);
}
```

3. **压力测试**:
```typescript
// 同时测试多个功能
await Promise.all([
  testChat(),
  testNotes(),
  testSearch(),
]);
```

## 集成到CI/CD

### GitHub Actions 示例

```yaml
name: Comprehensive Integration Test

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: 20
          
      - name: Install dependencies
        run: |
          cd backend-node
          npm ci
          
      - name: Run comprehensive test
        run: |
          cd backend-node
          npm test tests/e2e/comprehensive-integration.e2e.test.ts
        env:
          DATABASE_URL: postgresql://postgres:test@localhost:5432/scholarai
          REDIS_URL: redis://localhost:6379
          JWT_SECRET: test-secret
```

## 调试技巧

### 1. 单步调试

使用 Jest 的 `--detectOpenHandles` 选项：

```bash
jest tests/e2e/comprehensive-integration.e2e.test.ts --detectOpenHandles --runInBand
```

### 2. 日志输出

在测试中添加详细日志：

```typescript
console.log('Request:', JSON.stringify(requestBody, null, 2));
console.log('Response:', JSON.stringify(response.body, null, 2));
```

### 3. 检查数据库状态

```bash
# 连接到PostgreSQL
psql -U postgres -d scholarai

# 查看测试用户
SELECT * FROM users WHERE email LIKE '%example.com';

# 查看测试论文
SELECT * FROM papers WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%example.com');
```

## 测试数据清理

测试脚本在 `afterAll` 中自动清理：

```typescript
afterAll(async () => {
  await cleanupTestData();
});
```

清理规则：
- 删除所有邮箱包含 `test-` 或 `@example.com` 的用户
- 删除关联的论文、笔记、查询记录
- 清理过期的Refresh Token

## 相关文档

- [测试策略文档](../README.md)
- [API文档](../../doc/swagger.json)
- [架构文档](../../doc/架构/系统架构图.md)
- [前端集成研究](../../doc/前端集成研究/)
- **[PDF处理流程详解](./PDF-PROCESSING-STAGES.md)** ⭐ 新增
- [PDF并行流水线](../../doc/PDF_PARALLEL_PIPELINE.md)

## 支持

如有问题，请检查：
1. 后端服务日志：`backend-node/logs/` 和 `backend-python/logs/`
2. 数据库日志：`docker logs scholarai-postgres`
3. Python服务日志：`docker logs scholarai-python`

或联系开发团队。