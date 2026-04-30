# 项目二阶段产品化审查清单

> 生成日期: 2026-04-20  
> 审查范围: scholar-ai 全仓库 (apps/web + apps/api + infra + packages)  
> 审查方法: 基于源码全量阅读的证据驱动审查

---

## 一、仓库盘点

### A. 仓库结构总览

| 目录 | 职责 |
|------|------|
| `apps/web/` | React + Vite 前端, Tailwind CSS, Zustand, React Query |
| `apps/api/` | FastAPI + SQLAlchemy 2.0 异步后端, Celery worker |
| `packages/sdk/` | 前端 SDK 封装 (HTTP client, API types) |
| `packages/types/` | 前后端共享类型契约 |
| `packages/config/` | 共享配置 |
| `packages/ui/` | 共享 UI 组件 (预留) |
| `infra/` | Docker, Nginx, 部署脚本, 可观测性配置 |
| `docs/` | 架构文档, ADR, 治理, 工程规范 |
| `tests/` | E2E, 集成, 单元测试 |
| `scripts/` | 治理检查, 基准测试, 部署脚本 |

### B. 前端页面清单

| Route | 入口文件 | 页面名称 | 主要依赖 | Loading/Empty/Error | 风险 |
|-------|---------|---------|---------|---------------------|------|
| `/` | Landing.tsx | 着陆页 | magazine.css | ✅/✅/N/A | Low |
| `/login` | Login.tsx | 登录 | AuthContext | ✅/N/A/✅ | Low |
| `/register` | Register.tsx | 注册 | AuthContext | ✅/N/A/✅ | Low |
| `/forgot-password` | ForgotPassword.tsx | 忘记密码 | authApi | ✅/N/A/✅ | Low |
| `/reset-password` | ResetPassword.tsx | 重置密码 | authApi | ✅/N/A/✅ | Low |
| `/dashboard` | Dashboard.tsx | 仪表盘 | dashboardApi, recharts | ✅/partial/✅ | Medium |
| `/knowledge-bases` | KnowledgeBaseList.tsx | 知识库列表 | kbApi | ✅/✅/✅ | Medium |
| `/knowledge-bases/:id` | KnowledgeBaseDetail.tsx | 知识库详情 | KnowledgeBaseWorkspace | ✅/partial/partial | Medium |
| `/search` | Search.tsx | 检索 | SearchWorkspace | ✅/✅/✅ | Medium |
| `/read/:id` | Read.tsx | 论文阅读 | PDFViewer, annotations | ✅/partial/partial | High |
| `/chat` | Chat.tsx → ChatWorkspace → ChatWorkspaceV2 | 终端对话 | SSE, useChatStream | ✅/✅/✅ | **Critical** |
| `/notes` | Notes.tsx | 笔记 | notesApi | ✅/✅/partial | Medium |
| `/settings` | Settings.tsx | 设置 | usersApi, settingsStore | ✅/N/A/partial | Low |

### C. 后端模块清单

| 模块路径 | 职责 | 对外 API | DB/Stream/Task | 风险 |
|---------|------|---------|----------------|------|
| `api/auth.py` | 认证 | register/login/refresh/logout/me | DB+Redis | Medium |
| `api/chat.py` | 聊天流式 | /chat/stream, /chat/confirm | SSE+DB | **Critical** |
| `api/session.py` | 会话 CRUD | sessions/ | DB | Low |
| `api/uploads.py` | 文件上传 | /uploads | DB+FileStorage+Task | High |
| `api/papers/` | 论文管理 | papers/, papers/:id/* | DB+Milvus+Neo4j | High |
| `api/kb/` | 知识库 | kb/, kb/:id/search, kb/:id/qa | DB+Milvus | High |
| `api/imports/` | 批量导入 | imports/ | DB+Redis+Celery | High |
| `api/search/` | 统一检索 | /search | Milvus+S2API+arXiv | Medium |
| `api/rag.py` | RAG 检索 | /rag/query | Milvus+Reranker | Medium |
| `api/tasks.py` | 任务状态 | /tasks/:id | DB | Low |
| `services/chat_orchestrator.py` | Agent 编排 | (internal) | LLM+Tool+SSE | **Critical** |
| `services/paper_service.py` | 论文业务 | (internal) | DB+File+Milvus | High |
| `services/import_job_service.py` | 导入任务 | (internal) | DB+Redis+Celery | High |
| `workers/import_worker.py` | 导入 worker | (Celery task) | DB+File+AI | High |
| `workers/storage_manager.py` | 处理管线 | (Celery task) | DB+Milvus+Neo4j+LLM | High |
| `core/milvus_service.py` | 向量存储 | (internal) | Milvus | Medium |
| `core/docling_service.py` | PDF 解析 | (internal) | Docling | Medium |
| `core/safety_layer.py` | Agent 安全层 | (internal) | - | Medium |

### D. 审查范围补充 — 用户未点名但必须审查的项

1. **前端状态双源/三源同步** — chatStore + chatWorkspaceStore + useSessions + useChatMessagesViewModel 四层状态
2. **SSE 断线重连与幂等性** — sseService 重连后是否重播/去重
3. **前端 bundle 分析** — 是否存在过大 vendor chunk
4. **packages/ SDK 与 services/ 的冗余** — sdkHttpClient vs 直接 fetch 双路径并存
5. **Legacy 桥接代码存活** — ChatLegacy.tsx, rollout.ts 已完成但未清理
6. **后端 app/legacy/ 目录** — 是否仍有运行时引用
7. **数据库迁移脚本一致性** — alembic migrations vs 模型定义
8. **Neo4j/Milvus 连接池与故障隔离** — 单组件故障是否影响核心功能

---

## 二、审查清单 — 按优先级与分类

### P0: 必须立即处理

| # | 类别 | Item | Why it Matters | Evidence | Owner | Expected Output |
|---|------|------|----------------|----------|-------|-----------------|
| P0-01 | Security | JWT 默认密钥 `"change-me-in-production"` / `"test-secret-key-for-development-only"` | 非 production 环境（staging/dev）使用弱密钥，可伪造任意 token | [config.py](apps/api/app/config.py) `JWT_SECRET_KEY` | Backend | 启动校验非默认值，所有环境强制 |
| P0-02 | Security | 路径遍历防护不完整 — `replace("../", "")` 可用 `....//` 绕过 | 攻击者可读取/删除服务器任意文件 | [storage.py](apps/api/app/core/storage.py) `_get_local_path()` | Backend | 改用 `Path.resolve()` + 根路径前缀校验 |
| P0-03 | Security | `paper_service.py` 文件删除绕过 StorageService | 直接拼接路径 `f"{settings.LOCAL_STORAGE_PATH}/{storage_key}"` 无路径校验 | [paper_service.py](apps/api/app/services/paper_service.py) `delete_paper_for_api` | Backend | 改走 `StorageService.delete_file()` |
| P0-04 | Security | 认证端点 (login/register) 无速率限制 | 暴力破解/撞库/注册轰炸 | [auth.py](apps/api/app/api/auth.py) — 无 RateLimiter 装饰器 | Backend | 添加 SlowAPI 速率限制 |
| P0-05 | Chat UX | ChatWorkspaceV2 过重 (~800行) — scope 验证、SSE 管理、状态同步全堆一起 | 维护困难，任何 Chat 改动风险极高 | [ChatWorkspaceV2.tsx](apps/web/src/features/chat/workspace/ChatWorkspaceV2.tsx) | Frontend | 拆分为 scope 验证 hook + SSE 连接管理 hook |
| P0-06 | Chat UX | 四层消息状态源并存 — chatStore / chatWorkspaceStore / useSessions / useChatMessagesViewModel | 状态同步 bug 高发区，已有 placeholder 绑定逻辑复杂化 | 四个文件交叉引用 | Frontend | 统一为 useChatMessagesViewModel 单一 truth source |

### P1: 近期处理

| # | 类别 | Item | Why it Matters | Evidence | Owner | Expected Output |
|---|------|------|----------------|----------|-------|-----------------|
| P1-01 | Backend Arch | `chat_orchestrator.py` 1100+ 行超限 | 不可测、不可维护 | [chat_orchestrator.py](apps/api/app/services/chat_orchestrator.py) | Backend | 拆为 SSE 序列化器 + Phase 推断器 + Agent 执行器 |
| P1-02 | Backend Stability | ImportJob 状态机无转换守卫 | 可能出现非法状态跳转 | [import_job_service.py](apps/api/app/services/import_job_service.py) `update_status` | Backend | 增加合法转换表 |
| P1-03 | Backend Stability | 异步上下文中同步 I/O (`os.path.exists`, `os.remove`) | 阻塞事件循环 | [paper_service.py](apps/api/app/services/paper_service.py) | Backend | 改用 `aiofiles` / `asyncio.to_thread()` |
| P1-04 | Backend Arch | 错误响应格式三种并存 (RFC 7807 / Errors.not_found / HTTPException) | 前端错误处理分裂 | auth.py vs kb_crud.py vs imports/jobs.py | Backend | 统一为 RFC 7807 ProblemDetail |
| P1-05 | Backend Arch | Service 模式不一致 (静态方法/实例/模块函数/单例混用) | 依赖注入不可能，测试困难 | paper_service vs auth_service vs chat_orchestrator | Backend | 统一为实例 + DI |
| P1-06 | Frontend Perf | MessageFeed 无虚拟化 — 长对话渲染全量 DOM | 50+ 消息后明显卡顿 | [MessageFeed.tsx](apps/web/src/features/chat/components/message-feed/MessageFeed.tsx) | Frontend | 引入 virtualized list (react-window) |
| P1-07 | Frontend UX | Chat 右侧面板 `hidden xl:block` — 1280px 以下不可见 | 大量用户看不到 Agent 状态/Token 监控 | [ChatRightPanel.tsx](apps/web/src/features/chat/components/ChatRightPanel.tsx) | Frontend | 改为 bottom sheet 或 popover |
| P1-08 | Frontend UX | Dashboard 页面三次独立数据请求 (stats + recentPapers + recentSessions) | 首屏加载慢，3 个 loading 状态 | [Dashboard.tsx](apps/web/src/app/pages/Dashboard.tsx) 3 个 useEffect | Frontend | 合并为单一 useDashboardData hook |
| P1-09 | Frontend UX | Notes.tsx ~870 行 — 单文件巨型组件 | 不可维护 | [Notes.tsx](apps/web/src/app/pages/Notes.tsx) | Frontend | 拆分 NoteList + NoteEditor + NoteFolderTree |
| P1-10 | Security | Token 黑名单依赖 Redis — Redis 宕机时已吊销 token 仍可用 | 安全降级风险 | [auth_service.py](apps/api/app/services/auth_service.py) `verify_token` | Backend | Redis 不可用时 fail-closed |
| P1-11 | Backend Perf | SemanticCache 使用 Redis `scan_iter` + 余弦相似度全量扫描 — $O(n)$ | 缓存量增长后严重退化 | [semantic_cache.py](apps/api/app/core/semantic_cache.py) | Backend | 改用 Milvus 向量索引 |
| P1-12 | Frontend DX | Legacy 桥接代码未清理 — ChatLegacy.tsx, rollout.ts 仍存活 | 增加理解负担，无实际作用 | ChatLegacy.tsx 注释 "LEGACY BRIDGE" | Frontend | 删除 |
| P1-13 | Tech Debt | `app/core/` 目录含 4 个测试文件 | 生产包含测试代码 | test_image_extractor.py 等 | Backend | 移至 tests/ |
| P1-14 | Tech Debt | `milvus_service.py.backup` 存在于代码仓库 | 死文件 | app/core/milvus_service.py.backup | Backend | 删除 |
| P1-15 | Frontend Design | 杂志风格 CSS (magazine.css) 仅用于 Landing — Chat/Dashboard 内有零散 font-serif 但无系统性表达 | 设计语言碎片化 | magazine.css vs 各页面内联 class | Design+FE | 统一 editorial design token 到 theme.css |

### P2: 可排期优化

| # | 类别 | Item | Why it Matters | Evidence | Owner | Expected Output |
|---|------|------|----------------|----------|-------|-----------------|
| P2-01 | Backend | 合并两套 RateLimiter (search/shared.py + import_rate_limiter.py) | 代码重复 | 两个文件 | Backend | 提取共享基类 |
| P2-02 | Backend | Repository 覆盖不完整 — 仅 4 个 repo，其余 service 直接查 DB | 数据访问层不统一 | auth_service, task_service 等 | Backend | 补齐 |
| P2-03 | Backend | Neo4j 批量写入优化 — 逐条 Cypher MERGE | 建图慢 | neo4j_service.py, graph_builder.py | Backend | 改用 UNWIND |
| P2-04 | Backend | ImportJob 事件日志仅写 logger — 前端无法查询 | 用户无法跟踪导入详情 | import_job_service.py `add_event` 注释 | Backend | 实现 import_job_events 表 |
| P2-05 | Backend | Paper 表缺少 `file_sha256` — 去重仅靠 ImportJob 表 | 直接上传的论文无法被导入去重命中 | import_dedupe_service.py 注释 | Backend | Paper 表加 sha256 字段 |
| P2-06 | Backend | Celery worker_concurrency=1 + solo pool | PDF 处理吞吐受限 | celery_config.py | Backend | 评估提高并发 |
| P2-07 | Backend | `import_worker.py` 800+ 行含完整状态机 | 过重不可测 | import_worker.py | Backend | 拆分 |
| P2-08 | Frontend | Dashboard.tsx 515 行 — 图表/KPI/列表全堆一起 | 维护难 | Dashboard.tsx | Frontend | 拆为 DashboardKPI + DashboardCharts + DashboardRecent |
| P2-09 | Frontend | Read.tsx 650 行 — PDF 阅读器 + 注释 + 侧边栏 | 过重 | Read.tsx | Frontend | 拆分 |
| P2-10 | Frontend | KnowledgeBaseList.tsx 570 行 | 过重 | KnowledgeBaseList.tsx | Frontend | 拆分 |
| P2-11 | Observability | 后端 request_id/trace_id 未系统性传播 | 排障困难 | 无统一中间件 | Backend | 添加 correlation ID 中间件 |
| P2-12 | Testing | core/ 服务层测试覆盖不明 — agentic_retrieval, multimodal_search 缺测试 | 核心 RAG 路径无保护 | tests/ 目录 | Backend | 补充 |
| P2-13 | DX | packages/sdk 与 services/ 冗余 — sdkHttpClient 与直接 fetch 双路径 | API 调用方式不统一 | services/chatApi.ts 混用 sdk + sdkHttpClient | Frontend | 统一走 SDK |
| P2-14 | Frontend | MarkdownRenderer 加载 rehype-mermaid — 大依赖 | Bundle 增大 | MarkdownRenderer.tsx | Frontend | 动态 import |
| P2-15 | Accessibility | 全站无 ARIA landmark, skip-nav, 键盘导航测试 | 可访问性缺失 | Layout.tsx 无 role/aria 属性 | Frontend | 补充 |
| P2-16 | i18n | 硬编码中英文散落各组件 — 非 i18n 框架 | 扩展性差 | 各页面 `isZh ?` 三元 | Frontend | 评估引入 i18next |
| P2-17 | Config | CORS `ALLOWED_HOSTS: ["*"]` 默认值 — 仅 production 校验 | staging 环境开放 | config.py | Backend | 所有非 dev 环境收紧 |
| P2-18 | Backend | Deprecated shim 文件 (models/session.py, models/note.py, core/config.py) | 增加理解负担 | 多个重导出文件 | Backend | 清理 |
| P2-19 | Frontend | Layout.tsx 含 SVG 噪点纹理 overlay 全局覆盖 — z-50 | 性能开销 + 可能遮挡交互元素 | Layout.tsx `<svg>` z-50 | Frontend | 评估移除或降低 z-index |

---

## 三、Chat 页面专项审查

### 当前 Chat 页面总评

**架构**：ChatWorkspace → ChatRunContainer → ChatWorkspaceV2 三层嵌套，实际逻辑全在 ChatWorkspaceV2 (~800行)。ChatLegacy 和 rollout.ts 是历史遗留，rollout 已完成但未清理。

**与 ChatGPT 网页版的差距**：
1. **输入区不够稳定** — ComposerInput 位于底部但无固定吸附，模式切换按钮 (Auto/Fast RAG/Deep Agent) 增加认知负荷
2. **消息列表无虚拟化** — 长对话性能退化
3. **右侧面板 1280px 以下消失** — Agent 状态/Token 监控对大量用户不可见
4. **侧边栏搜索仅按标题过滤** — 无时间分组、无 pin 功能
5. **流式更新节流 100ms** — 合理，但缺少 progressive rendering
6. **引用面板内联展示** — 占据消息面积，应默认折叠

### 应保留的杂志风格元素
- Landing 页面的 editorial layout + paper texture
- 顶部导航的 serif 字体 + 小号大写字母标签
- 空状态的 editorial 插图风格
- 色彩体系 (#d35400 暖橙 + #ede0cee8 纸白)
- 卡片的 paper shadow token

### 应移除或降级的干扰项
- 聊天主阅读区的 font-serif → 改为 sans-serif (可读性优先)
- Layout 全局 SVG 噪点覆盖 → Chat 页面禁用或降 z-index
- ChatHeader 的 "Bot" 图标 → 不必要的装饰
- 右侧面板入场动画 (motion.div initial/animate) → 造成闪烁

### Chat 页面改版原则
1. **单主轴** — 中央对话区是唯一焦点，工具/引用退到二级层
2. **可读性优先** — sans-serif 正文，16px 行高 1.6-1.75
3. **功能分层** — 核心操作 (输入/发送/停止) 始终可见，次要操作 (模式/引用/reasoning) hover/折叠
4. **装饰退后** — 杂志风格保留在品牌元素 (logo/header/empty state)，不侵入消息流
5. **性能优先** — 虚拟化、lazy 加载 reasoning 面板、减少 re-render

### Chat 页面推荐目标形态
- **布局**: 左侧窄栏 (240px 会话列表) + 中央主对话区 + 右侧可选面板 (按需弹出，非固定)
- **输入区**: 底部固定吸附，单行默认可展开，模式选择简化为 dropdown/chip 而非三个按钮
- **消息区**: 虚拟化列表，user 消息右对齐紧凑，assistant 消息左对齐宽布局
- **侧边栏**: 时间分组 (Today/Yesterday/This Week)，支持 pin + 搜索
- **工具/上下文区**: reasoning/tools 默认折叠为 status line，展开为 inline accordion
- **视觉风格**: 消息区纯净 sans-serif，品牌色仅在 header + accent 使用
- **交互动线**: 输入 → 流式响应 (auto-scroll) → 完成 → 引用折叠可展开 → 下一轮输入

---

## 四、后端全面审查总结

### 当前成熟度判断
- **API 层**: 中等成熟 — 路由定义清晰但错误格式不统一
- **Service 层**: 中等 — 核心功能完备但模式混乱
- **数据层**: 较好 — SQLAlchemy 2.0 异步 + 清晰 ORM 模型
- **AI 管线**: 较好 — Agentic Retrieval + Safety Layer 分层清晰
- **安全性**: 有基础 (Argon2id + httpOnly cookie) 但有 P0 漏洞
- **可观测性**: 较弱 — 日志存在但缺少 structured logging + trace ID

### 最大风险
1. 路径遍历 (P0-02, P0-03)
2. chat_orchestrator 过重不可维护 (P1-01)
3. 状态一致性 — ImportJob 状态机无守卫 (P1-02)

### 最大技术债
1. Service 模式四种并存 (P1-05)
2. 错误格式三种混用 (P1-04)
3. import_worker.py 800+ 行 (P2-07)

---

## 五、主动增加审查项

### 5.1 前端 Bundle / Chunk Splitting
- **为什么必须审查**: MarkdownRenderer 静态引入 rehype-mermaid + katex — 非所有页面需要
- **当前优先级**: P2
- **影响**: 首屏 JS 体积增大

### 5.2 SEO / Metadata
- **为什么必须审查**: SPA 无 SSR/SSG，Landing 页面无 meta tags
- **当前优先级**: P2 (如果需要公开搜索引擎可见)
- **影响**: 搜索引擎不可索引

### 5.3 Feature Flag 残留
- **为什么必须审查**: rollout.ts 的 `VITE_CHAT_WORKSPACE_V2_ROLLOUT_PERCENT` 已 100% 但文件未删除
- **当前优先级**: P1 (P1-12)
- **影响**: 增加理解负担

### 5.4 环境变量与部署风险
- **为什么必须审查**: 生产 fallback URL `https://api.scholarai.com` 硬编码在 `api.ts`
- **当前优先级**: P2
- **影响**: 域名变更时需改代码

### 5.5 死代码与分叉实现
- **为什么必须审查**: ChatLegacy, ChatRunContainer, useChatSession 均为空壳 wrapper
- **当前优先级**: P1
- **影响**: 每个新贡献者都会困惑

### 5.6 文档与代码脱节
- **为什么必须审查**: `docs/specs/design/frontend/DESIGN_SYSTEM.md` 定义的 token 与 `theme.css` 实际 token 可能不一致
- **当前优先级**: P2
- **影响**: 设计实现漂移

### 5.7 回归风险最高区域
1. **ChatWorkspaceV2** — 任何改动影响全部对话功能
2. **chat_orchestrator.py** — Agent/RAG/streaming 全在这里
3. **import_worker.py** — 状态机复杂，测试覆盖不明
4. **paper_service.py** — 文件+DB+向量三重操作

---

> 此清单配合 `frontend-chat-productization-plan.md` 和 `backend-audit-remediation-plan.md` 使用。
