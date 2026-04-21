# 后端全面审计与整改执行方案

> 生成日期: 2026-04-20  
> 审查方法: 全量源码阅读 — app/ 全部模块 (api, services, core, models, schemas, repositories, middleware, workers, tasks, utils, legacy)  
> 定位: 可执行整改方案

---

## 1. 后端当前阶段判断

### 成熟度
- **API 层**: 中等 — 路由清晰，覆盖完整，但错误格式不统一
- **Service 层**: 中等偏弱 — 核心功能完备，但模式混乱 (静态/实例/函数/单例四种并存)
- **数据层**: 较好 — SQLAlchemy 2.0 async + 清晰 ORM，但 Repository 覆盖不完整
- **AI 管线**: 较好 — Agentic Retrieval + SafetyLayer + Tool Registry 分层清晰
- **安全性**: 有基础 (Argon2id, httpOnly, rate limiting) 但有 P0 漏洞
- **可观测性**: 较弱 — logger 存在但无 structured logging / trace ID 传播

### 最大风险
1. **路径遍历** — storage.py + paper_service.py 直接文件操作 (P0)
2. **chat_orchestrator 不可维护** — 1100+ 行单文件 (P1)
3. **ImportJob 状态一致性** — 无转换守卫 (P1)

### 最大技术债
1. Service 模式四种并存
2. 错误响应三种格式混用
3. import_worker.py 800+ 行巨型 worker

---

## 2. 问题分类与整改方案

### 2.1 安全问题 — P0 立即修复

#### S-01: JWT 默认密钥

- **Evidence**: [config.py](apps/api/app/config.py) `JWT_SECRET_KEY: str = "change-me-in-production"` / `"test-secret-key-for-development-only"`
- **Affected files**: `app/config.py`, `app/services/auth_service.py`
- **Root cause**: `validate_production_settings()` 仅在 `ENVIRONMENT=="production"` 时触发
- **Smallest safe fix**:
  ```python
  # config.py startup
  if self.JWT_SECRET_KEY in ("change-me-in-production", "test-secret-key-for-development-only"):
      if self.ENVIRONMENT != "development":
          raise RuntimeError("JWT_SECRET_KEY must be set in non-development environments")
  ```
- **Preferred direction**: 所有非 development 环境强制校验
- **Validation**: 启动 staging 不设环境变量 → 应 crash

#### S-02: 路径遍历防护不完整

- **Evidence**: [storage.py](apps/api/app/core/storage.py) `_get_local_path()` 仅做 `replace("../", "").replace("./", "")`
- **Affected files**: `app/core/storage.py`
- **Root cause**: 字符串替换可用 `....//` 绕过
- **Smallest safe fix**:
  ```python
  def _get_local_path(self, key: str) -> Path:
      base = Path(self.local_storage_path).resolve()
      target = (base / key).resolve()
      if not str(target).startswith(str(base)):
          raise ValueError(f"Path traversal attempt: {key}")
      return target
  ```
- **Validation**: 测试 `_get_local_path("../../etc/passwd")` → 应 raise

#### S-03: paper_service 文件删除绕过 StorageService

- **Evidence**: [paper_service.py](apps/api/app/services/paper_service.py) `delete_paper_for_api` 直接拼 `f"{settings.LOCAL_STORAGE_PATH}/{storage_key}"`
- **Affected files**: `app/services/paper_service.py`
- **Root cause**: 历史代码未走 StorageService 抽象
- **Smallest safe fix**: 改用 `storage_service.delete_file(storage_key)`
- **Validation**: 删除论文后确认文件被正确清理

#### S-04: 认证端点无速率限制

- **Evidence**: [auth.py](apps/api/app/api/auth.py) — `register`, `login`, `forgot-password` 无 RateLimiter
- **Affected files**: `app/api/auth.py`
- **Root cause**: 速率限制仅应用于搜索端点
- **Smallest safe fix**:
  ```python
  from app.middleware.rate_limit import rate_limiter
  
  @router.post("/login")
  @rate_limiter.limit("5/minute")
  async def login(...): ...
  
  @router.post("/register")
  @rate_limiter.limit("3/minute")
  async def register(...): ...
  ```
- **Validation**: 6 次快速 login → 第 6 次返回 429

#### S-05: Redis 宕机时 Token 黑名单失效

- **Evidence**: [auth_service.py](apps/api/app/services/auth_service.py) `verify_token` 查 Redis 黑名单
- **Affected files**: `app/services/auth_service.py`, `app/middleware/auth.py`
- **Root cause**: Redis 不可用时 token 验证跳过黑名单检查
- **Smallest safe fix**: Redis 不可用时 fail-closed (拒绝所有 token) 或降级为短 TTL
- **Validation**: 停止 Redis → 使用已 logout 的 token → 应拒绝

---

### 2.2 架构边界问题 — P1

#### A-01: chat_orchestrator.py 过大 (1100+ 行)

- **Evidence**: [chat_orchestrator.py](apps/api/app/services/chat_orchestrator.py) — `execute_with_streaming` 单方法 300+ 行
- **Affected files**: `app/services/chat_orchestrator.py`
- **Root cause**: SSE 序列化 + Phase 推断 + Agent 执行 + 工具管理混在一个类中
- **Smallest safe fix**: 提取 `SSEEventEmitter` 类 (序列化+发送 SSE 事件)
- **Preferred direction**:
  1. `SSEEventEmitter` — SSE 事件构造与发送
  2. `PhaseRouter` — 意图分类 → Phase → Agent 路由
  3. `AgentExecutor` — Agent 工具执行与收敛
  4. `ChatOrchestrator` — 编排上述三者
- **Validation**: 现有 chat 流式测试全通过

#### A-02: 错误响应三种格式混用

- **Evidence**:
  - auth.py: `ProblemDetail` (RFC 7807)
  - kb_crud.py: `Errors.not_found()` + `HTTPException`
  - imports/jobs.py: `Errors.not_found()` + `http_status` 别名
- **Affected files**: 所有 `app/api/*.py`
- **Root cause**: 不同开发阶段引入不同模式
- **Smallest safe fix**: 添加全局异常处理中间件统一输出 RFC 7807
- **Preferred direction**: 所有 router 使用 `Errors.*()` → 全局 exception handler 转为 ProblemDetail
- **Validation**: 所有错误响应 Content-Type 为 `application/problem+json`

#### A-03: Service 模式四种并存

- **Evidence**:
  | 模式 | 示例 |
  |------|------|
  | 静态方法类 | `PaperService.create_paper_for_api()` |
  | 实例方法类 | `ImportJobService(db)` |
  | 模块级函数 | `auth_service.register_user()` |
  | 单例 | `ChatOrchestrator()`, `get_storage_service()` |
- **Affected files**: 所有 `app/services/*.py`
- **Root cause**: 不同阶段不同作者
- **Smallest safe fix**: 不动现有代码，新代码统一用实例+DI
- **Preferred direction**: 渐进迁移为实例类 + `Depends()` 注入
- **Validation**: 新增 service 必须用实例模式 + 依赖注入

#### A-04: Repository 覆盖不完整

- **Evidence**: 仅 4 个 Repository (paper, knowledge_base, import_job, reading_progress)
- **Affected files**: `app/services/auth_service.py`, `app/services/task_service.py` 等直接执行 SQLAlchemy
- **Root cause**: Repository 模式后期引入，未全量覆盖
- **Smallest safe fix**: 不阻塞当前迭代，标记 TODO
- **Preferred direction**: 新增 `UserRepository`, `SessionRepository`, `TaskRepository`

---

### 2.3 稳定性问题 — P1

#### ST-01: ImportJob 状态机无转换守卫

- **Evidence**: [import_job_service.py](apps/api/app/services/import_job_service.py) `update_status` 接受任意 status/stage
- **Affected files**: `app/services/import_job_service.py`
- **Root cause**: 缺少合法转换表
- **Smallest safe fix**:
  ```python
  VALID_TRANSITIONS = {
      "created": {"queued"},
      "queued": {"running", "cancelled"},
      "running": {"awaiting_user_action", "completed", "failed", "cancelled"},
      "awaiting_user_action": {"running", "cancelled"},
  }
  
  def update_status(self, current: str, target: str):
      if target not in VALID_TRANSITIONS.get(current, set()):
          raise ValueError(f"Invalid transition: {current} -> {target}")
  ```
- **Validation**: 测试非法转换 (如 completed → running) → 应 raise

#### ST-02: 异步上下文中同步 I/O

- **Evidence**: [paper_service.py](apps/api/app/services/paper_service.py) 在 async 函数中调用 `os.path.exists()`, `os.remove()`
- **Affected files**: `app/services/paper_service.py`
- **Root cause**: 早期代码未考虑事件循环阻塞
- **Smallest safe fix**: `await asyncio.to_thread(os.remove, file_path)`
- **Validation**: 无阻塞，删除大文件时其他请求不受影响

#### ST-03: 批量删除无事务保护

- **Evidence**: `batch_delete_for_api` 循环删除，中途失败无回滚
- **Affected files**: `app/services/paper_service.py`
- **Root cause**: 文件删除与数据库操作未在同一事务中
- **Smallest safe fix**: 先删数据库记录 (可回滚) → 再异步删文件 (失败仅留孤儿文件)
- **Validation**: 模拟文件删除失败 → 数据库记录应已删除

#### ST-04: track_processing_stages 轮询

- **Evidence**: [import_job_service.py](apps/api/app/services/import_job_service.py) `asyncio.sleep(5)` 轮询循环最长 1 小时
- **Affected files**: `app/services/import_job_service.py`
- **Root cause**: 简单实现
- **Smallest safe fix**: 保持现状但加 max_retries 限制
- **Preferred direction**: Redis Pub/Sub 或 webhook 回调

---

### 2.4 性能问题 — P1/P2

#### P-01: SemanticCache 全量扫描 — O(n)

- **Evidence**: [semantic_cache.py](apps/api/app/core/semantic_cache.py) `scan_iter` + 逐 key 余弦相似度
- **Affected files**: `app/core/semantic_cache.py`
- **Root cause**: 使用 Redis 存储向量，无索引
- **Smallest safe fix**: 限制 cache size (LRU eviction)
- **Preferred direction**: 改用 Milvus 专用 collection 做语义缓存
- **Validation**: 1000 条缓存下查询 < 100ms

#### P-02: Neo4j 逐条 Cypher MERGE

- **Evidence**: [neo4j_service.py](apps/api/app/core/neo4j_service.py) `create_chunk_nodes` 逐条
- **Affected files**: `app/core/neo4j_service.py`, `app/core/graph_builder.py`
- **Root cause**: 简单实现
- **Smallest safe fix**: 改用 `UNWIND` 批量写入
- **Validation**: 100 chunks 建图时间 < 2s (当前 > 10s)

#### P-03: DoclingParser 创建 3 个 DocumentConverter 实例

- **Evidence**: [docling_service.py](apps/api/app/core/docling_service.py) `__init__` 创建 converter, native_converter, ocr_converter
- **Affected files**: `app/core/docling_service.py`
- **Root cause**: 三种配置需要三个实例
- **Smallest safe fix**: lazy init — 按需创建
- **Validation**: 内存占用减少

---

### 2.5 可观测性问题 — P2

#### O-01: 无 request correlation ID

- **Evidence**: 无统一 request_id 中间件
- **Affected files**: `app/middleware/`
- **Root cause**: 未实现
- **Smallest safe fix**:
  ```python
  @app.middleware("http")
  async def correlation_id_middleware(request, call_next):
      request_id = request.headers.get("X-Request-ID", str(uuid4()))
      logger.bind(request_id=request_id)
      response = await call_next(request)
      response.headers["X-Request-ID"] = request_id
      return response
  ```
- **Validation**: 每个日志行包含 request_id

#### O-02: ImportJob 事件仅写 logger

- **Evidence**: [import_job_service.py](apps/api/app/services/import_job_service.py) `add_event` 注释 "Wave 3 deferred"
- **Affected files**: `app/services/import_job_service.py`
- **Root cause**: 表未建
- **Smallest safe fix**: 保持 logger，前端通过 status polling 获取进度
- **Preferred direction**: 建 `import_job_events` 表 + 前端 timeline 展示

---

### 2.6 可维护性问题 — P2

#### M-01: import_worker.py 800+ 行

- **Evidence**: [import_worker.py](apps/api/app/workers/import_worker.py) 含完整状态机 + 10 阶段 + source adapter
- **Affected files**: `app/workers/import_worker.py`
- **Root cause**: 所有导入逻辑集中一处
- **Smallest safe fix**: 提取 `ImportStateMachine` 和 `SourceDownloader`
- **Preferred direction**: 每个处理阶段独立函数/类

#### M-02: Deprecated shim 文件

- **Evidence**: `models/session.py`, `models/note.py`, `models/rag.py`, `core/config.py` 仅做 re-export
- **Affected files**: 上述文件
- **Root cause**: 重构后的兼容层
- **Smallest safe fix**: grep 引用 → 更新 import → 删除 shim

#### M-03: app/core/ 含测试文件

- **Evidence**: `test_image_extractor.py`, `test_milvus_unified.py` 等 4 个文件在 app/core/
- **Affected files**: `app/core/test_*.py`
- **Root cause**: 开发时放错位置
- **Smallest safe fix**: 移至 `tests/unit/core/`

#### M-04: 备份文件在仓库中

- **Evidence**: `app/core/milvus_service.py.backup`
- **Smallest safe fix**: 删除

#### M-05: RetrievedChunk 归一化代码重复

- **Evidence**: `_normalize_hit()` 在 multimodal_search_service.py, agentic_retrieval.py, rag.py 三处各自实现
- **Smallest safe fix**: 提取 `normalize_retrieval_chunk()` 到 `app/core/retrieval_utils.py`

---

## 3. 执行顺序

### P0 (本周)
1. S-01: JWT 默认密钥启动校验
2. S-02: storage.py 路径遍历修复
3. S-03: paper_service 文件删除走 StorageService
4. S-04: auth 端点加速率限制
5. S-05: Redis 宕机 fail-closed

### P1 (本迭代 — 2 周)
1. A-02: 统一错误响应格式 (全局异常处理中间件)
2. ST-01: ImportJob 状态机转换守卫
3. ST-02: 同步 I/O 改异步
4. A-01: chat_orchestrator 拆分 (提取 SSEEventEmitter 优先)
5. P-01: SemanticCache 加 LRU 限制

### P2 (下一迭代)
1. P-02: Neo4j 批量写入
2. O-01: request correlation ID
3. M-01: import_worker 拆分
4. M-02~M-05: 清理 shim / test files / backup / 重复代码
5. A-03: 新代码统一 Service 模式

---

## 4. 建议补充

### 该补哪些日志
- `chat_orchestrator.py`: Agent 执行每个 Phase 的耗时 + token
- `import_worker.py`: 每个阶段的进入/退出/耗时
- `storage_service.py`: 文件操作 (upload/delete/download) + 文件大小

### 该补哪些 metrics / tracing
- API 响应时间 P50/P95/P99 (FastAPI middleware)
- SSE 流连接数 (gauge)
- Milvus 查询耗时 (histogram)
- Celery 任务排队时间 + 执行时间
- 活跃 SSE 连接数

### 该补哪些测试
- `chat_orchestrator.py`: 单元测试 — 各 Phase 路由 + SSE 事件序列
- `import_worker.py`: 集成测试 — 状态机完整流程 (happy path + error recovery)
- `storage.py`: 路径遍历攻击测试
- `auth.py`: 速率限制测试
- `paper_service.py`: 批量删除事务回滚测试

### 该建立哪些 coding guardrails
- PR 检查: 新增 service 必须用实例 + DI
- PR 检查: 错误响应必须用 ProblemDetail
- PR 检查: 文件操作必须走 StorageService
- CI: `grep -r "os.remove\|os.path.exists\|os.unlink" app/services/ app/api/` → 应为 0
- CI: 文件行数检查 — 单文件 > 500 行报警, > 800 行阻塞

---

## 5. 最终验收标准

### 怎样算整改完成
- [ ] P0 全部 5 项修复并有测试覆盖
- [ ] P1 中 A-02 (错误统一) + ST-01 (状态机) + ST-02 (异步 I/O) 完成
- [ ] `chat_orchestrator.py` < 600 行
- [ ] 无路径遍历漏洞 (安全测试通过)
- [ ] 认证端点有速率限制 (测试通过)
- [ ] staging 环境启动时校验 JWT 密钥

### 怎样算可进入下一阶段开发
- [ ] P0 全部关闭
- [ ] P1 至少 60% 关闭
- [ ] 核心模块 (chat_orchestrator, import_worker) 有基本单元测试
- [ ] 全局异常处理中间件生效
- [ ] request correlation ID 可用
- [ ] CI 中有文件行数 + 禁用 os.remove 检查
