# ScholarAI 前端全量测试文档

> 日期：2026-05-04  
> 范围：`apps/web` 当前真实前端  
> 性质：可执行测试 runbook 与执行清单，不替代 release verdict  
> 重点：覆盖每一个页面与关键子页面，特别关注 Chat 页面

## 1. 目标与真源

本测试文档不是通用 QA 模板，而是基于当前仓库真实代码组织出的前端测试清单。文档目标有三类：

1. 给浏览器 walkthrough、Playwright E2E、Vitest 页面测试提供统一覆盖框架。
2. 明确每个页面、子页面、面板、tab、弹窗需要确认什么 UI、测试什么功能。
3. 优先暴露当前主链阻断面，尤其是 Chat、KB、Read、Upload、Notes 和 Compare。

本文件直接依据以下真源整理：

1. 路由真源：
   - `apps/web/src/app/routes.tsx`
2. 页面与工作区真源：
   - `apps/web/src/app/pages/*`
   - `apps/web/src/features/*`
3. 测试策略真源：
   - `docs/specs/development/testing-strategy.md`
4. 已有自动化覆盖：
   - `apps/web/e2e/*`
   - `apps/web/src/**/*.test.ts`
   - `apps/web/src/**/*.test.tsx`

## 2. 当前真实页面范围

公开页面：

1. `/`
2. `/home`
3. `/login`
4. `/register`
5. `/forgot-password`
6. `/reset-password`

受保护页面：

1. `/workspace` -> 重定向到 `/dashboard`
2. `/dashboard`
3. `/search`
4. `/knowledge-bases`
5. `/knowledge-bases/:id`
6. `/read`
7. `/read/:id`
8. `/chat`
9. `/notes`
10. `/compare`
11. `/analytics`
12. `/settings`

全局壳层：

1. `Layout`
2. 左侧导航
3. 最近对话区
4. 最近知识库区
5. 用户区
6. 移动端菜单

## 3. 测试分层与执行顺序

建议执行顺序：

1. 静态与类型层：
   - `cd apps/web && npm run type-check`
2. 组件/页面单测层：
   - `cd apps/web && npm run test:run`
3. 核心链路 E2E：
   - `cd apps/web && npm run test:e2e:ci`
4. 补充定向 E2E：
   - `chat-evidence.spec.ts`
   - `compare-critical.spec.ts`
   - `notes-rendering.spec.ts`
   - `user-journey.spec.ts`
   - `pr19-stepwise-flow.spec.ts`
5. 手工浏览器 walkthrough：
   - 逐页 UI
   - 失败态
   - 响应式
   - 权限与回跳

浏览器工具优先级：

1. `Chrome DevTools MCP`：
   - 默认主工具
   - 用于逐页导航、DOM 检查、控制台/网络排障、截图、性能与资源证据采集
2. `Computer Use`：
   - 作为视觉级交互补充
   - 用于真实点击、滚动、菜单、遮挡、悬浮、响应式布局确认
3. `browser-use`：
   - 仅作为备用
   - 只在 MCP 不可用或明确需要其 CLI 形态时启用

推荐测试层定义：

1. 页面 UI smoke：
   - 页面是否可进入
   - 主要区域是否出现
   - 关键 CTA 是否存在
2. 页面功能测试：
   - 主要交互是否成功
   - URL / query param / tab 状态是否一致
3. 集成测试：
   - 页面到 service 的主链是否通
   - handoff / SSE / import / search / read / notes 状态是否一致
4. E2E 测试：
   - 跨页面任务链是否可完成
5. 响应式与可访问性抽检：
   - 手机宽度下导航、输入区、按钮、滚动和遮挡是否正常

## 3.1 可执行环境准备

执行前确认本地服务与测试账号：

1. 基础服务：
   - Postgres
   - Redis
   - Neo4j
   - Milvus
   - MinIO / object storage
2. 后端 API：
   - `http://localhost:8000`
3. 前端 Vite：
   - `http://localhost:5173`
4. 固定测试账号：
   - email: `pr19-e2e@example.com`
   - password: `Pr19E2EPass123`
5. 可上传 PDF fixture：
   - `apps/api/tests/fixtures/pdfs/test_5_pages.pdf`
   - `apps/api/tests/fixtures/pdfs/test_10_pages.pdf`

推荐启动命令：

```bash
docker compose up -d postgres redis neo4j etcd minio milvus-standalone
cd apps/api && PYTHONPATH=$(pwd) .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
cd apps/api && PYTHONPATH=$(pwd) .venv/bin/celery -A app.core.celery_config:celery_app worker --pool=solo --loglevel=info --concurrency=1 -Q celery,import.process,import.finalize,pdf.process
cd apps/web && npm run dev -- --host 0.0.0.0 --port 5173
```

固定账号准备命令：

```bash
cd apps/api && .venv/bin/python scripts/ensure_e2e_test_user.py
```

健康检查：

```bash
curl -s http://localhost:8000/api/v1/system/health
curl -s http://localhost:5173
pgrep -fl "uvicorn|celery|vite"
```

## 3.2 浏览器工具执行规则

默认执行规则：

1. 优先使用 `Chrome DevTools MCP` 完成页面打开、元素检查、控制台/网络检查、截图和脚本探针。
2. 遇到视觉层判断、复杂 hover/menu、拖拽、滚动定位、遮挡验证时，补充使用 `Computer Use`。
3. 只有在 MCP 路径不可用、失真或明确需要 `browser-use` CLI 的场景下，才启用 `browser-use`。

### 3.2.1 browser-use 备用规则

`browser-use` 的元素 index 每次页面变化后都可能变化，所以执行规则固定为：

1. 每个页面先运行：
   - `browser-use open <url>`
   - `browser-use state`
2. 根据 `state` 返回的 index 执行：
   - `browser-use click <index>`
   - `browser-use input <index> "<text>"`
   - `browser-use upload <index> <file>`
3. 每个关键动作后都要执行：
   - `browser-use state`
   - 必要时 `browser-use screenshot <path>`
4. 如果 browser-use session 损坏：
   - `browser-use close`
   - 重新 `browser-use open http://localhost:5173`

当前本机若遇到 `browser-use` 相关 daemon/session/Chrome 残留、或 Python 3.14 event loop 报错：

```text
RuntimeError: There is no current event loop in thread 'MainThread'.
```

处理顺序：

1. 先记录为 `TOOLING-BLOCKED`，不是产品页面失败。
2. 尝试 `browser-use close --all` 后重跑。
3. 若存在残留 daemon、`Python.app`、`browser-use-user-data-dir-*` 或受管 Chrome 实例，先清理残留，再决定是否继续。
4. 若仍失败，切回 `Chrome DevTools MCP` 或 `Computer Use` 执行同一 runbook，并在缺陷记录中明确写明浏览器工具 fallback。

## 3.3 执行证据目录与命名

浏览器截图不要提交到仓库，建议落到本地临时目录：

```bash
mkdir -p /tmp/scholarai-frontend-full-test/$(date +%Y%m%d-%H%M%S)
```

证据命名规则：

1. `01-landing-home.png`
2. `02-login-success.png`
3. `03-dashboard-command-center.png`
4. `04-chat-streaming-answer.png`
5. `05-kb-upload-complete.png`
6. `06-read-source-highlight.png`

失败记录格式：

```markdown
### FAIL-<page>-<number>
- route:
- viewport:
- account:
- action:
- expected:
- actual:
- screenshot:
- console/network evidence:
- suspected owner: frontend | backend | data | tooling
- severity: blocker | high | medium | low
```

## 4. 全局跨页断言

所有页面都应检查以下公共项：

1. 受保护路由在未登录时是否回到 `/login`。
2. 已登录状态下访问 `/login` 是否自动跳去 `/dashboard`。
3. 顶层布局切换页面后，左侧导航 active 状态是否正确。
4. 页面标题、按钮、表格、输入框在常见桌面宽度和窄屏下是否不溢出。
5. loading / empty / error 三态是否都有可见反馈。
6. query param 驱动的页面状态刷新后是否能恢复。
7. 从一个页面 handoff 到另一个页面后，返回路径是否保真。
8. 不同工作区切换时，上一页状态不会污染当前页面。
9. 浏览器控制台没有 React duplicate key、hydration mismatch、uncaught exception。
10. 页面主链请求没有未解释的 401 / 403 / 404 / 500。
11. 线上模型状态展示与后端配置一致：embedding 为 DashScope `text-embedding-v4`，rerank 为 DashScope `qwen3-rerank`，generation 为在线 GLM。
12. partial / insufficient evidence / abstain 必须诚实展示原因，不可伪装成成功回答。
13. Evidence 跳转使用业务 `source_chunk_id` / `chunk_id`，不可把 Milvus auto-id 当成前端 source id。
14. 同一轮测试中的 `kb_id`、`paper_id`、`source_chunk_id` 必须贯穿 KB、Read、Chat、Notes、Compare，不允许各页面使用互相不一致的 fixture。

建议在每个页面打开后执行一次资源错误探针：

```bash
browser-use eval "performance.getEntriesByType('resource').filter(e => e.responseStatus && e.responseStatus >= 400).map(e => ({name: e.name, status: e.responseStatus}))"
```

若探针返回 4xx/5xx，测试记录必须写明是否为预期未登录、空数据、后端缺口或真实回归。

全局登录步骤：

```bash
browser-use open http://localhost:5173/login
browser-use state
# 找到 email input、password input、提交按钮后执行：
browser-use input <email_index> "pr19-e2e@example.com"
browser-use input <password_index> "Pr19E2EPass123"
browser-use click <submit_index>
browser-use state
browser-use screenshot /tmp/scholarai-frontend-full-test/login-dashboard.png
```

通过标准：

1. URL 到达 `/dashboard`。
2. 页面出现 Dashboard 主内容。
3. 左侧 `Layout` 导航出现。
4. 没有 401 toast 或登录错误。
5. 资源错误探针没有未解释的 4xx/5xx。

主线数据准备步骤：

1. 进入 `/knowledge-bases`。
2. 如果没有可用知识库，创建一个测试知识库，建议命名 `frontend-full-test-YYYYMMDD-HHMM`。
3. 进入该知识库。
4. 打开 `uploads` tab。
5. 上传 `apps/api/tests/fixtures/pdfs/test_5_pages.pdf`。
6. 等待 `papers` 数量和 `chunks` 数量刷新。
7. 进入 `search` tab，用 `method`、`results`、`introduction` 等简单词检索，确认有 evidence 结果。

主线数据通过标准：

1. `paperCount >= 1`。
2. `chunkCount > 0`。
3. KB search 返回至少 1 条 evidence。
4. evidence 点击可进入 `/read/:paperId`。
5. `/read/:paperId` 可加载 PDF viewer、source highlight 或 evidence sidenote。
6. `/chat?paperId=<paper_id>` 可进入单论文作用域。
7. `/chat?kbId=<kb_id>` 可进入整库作用域。
8. 若上传 job 失败，失败原因必须出现在 `import-status`，不可长期停留在 pending/preparing。

该数据后续供 KB、Read、Chat、Notes、Compare 复用。

## 5. 页面级测试矩阵

## 5.1 Layout 壳层

代码入口：

1. `apps/web/src/app/components/Layout.tsx`

必须确认的 UI：

1. 左侧工作区导航
2. 最近对话区
3. 最近知识库区
4. 用户信息区
5. 设置按钮
6. 退出按钮
7. 移动端菜单按钮

必须测试的功能：

1. 左侧栏展开/收起状态持久化到 `localStorage`
2. 点击 “新对话” 是否进入 `/chat?new=1`
3. 点击最近对话是否进入 `/chat?session=:id`
4. 点击最近知识库是否进入对应 KB 详情
5. 点击设置是否进入 `/settings`
6. 点击退出是否登出并回到首页
7. 移动端菜单开合是否正常

失败/边界：

1. 无会话时最近对话空态
2. 无知识库时资料馆藏区空态
3. `sessions` 或 `knowledgeBases` 加载中是否显示 loading

执行步骤：

```bash
browser-use open http://localhost:5173/dashboard
browser-use state
browser-use screenshot /tmp/scholarai-frontend-full-test/layout-dashboard.png
```

操作与预期：

1. 点击左侧每个主导航，预期 URL 分别进入 `/dashboard`、`/analytics`、`/chat`、`/search`、`/knowledge-bases`、`/notes`。
2. 点击收起侧栏，预期只保留图标；刷新后仍保持收起。
3. 点击展开侧栏，预期恢复文字标签。
4. 点击新对话，预期 URL 为 `/chat?new=1` 或进入 Chat 新会话状态。
5. 点击设置图标，预期进入 `/settings`。

记录项：

1. `layout-dashboard.png`
2. `layout-collapsed.png`
3. `layout-mobile-menu.png`

## 5.2 Landing

代码入口：

1. `apps/web/src/app/pages/Landing.tsx`

必须确认的 UI：

1. 顶部导航
2. Hero 主 CTA
3. 锚点滚动按钮
4. 功能、技术、用户评价、页脚区块

必须测试的功能：

1. `/` 与 `/home` 是否都能进入
2. 未登录点击 “开始探索” 是否进 `/login`
3. 已登录点击 “开始探索” 是否进 `/dashboard`
4. 顶部锚点按钮是否滚动到正确 section
5. 登录链接是否进入 `/login`

失败/边界：

1. 页面资源加载慢时是否仍可交互
2. 首屏在桌面与移动端是否保持可读，不出现遮挡

执行步骤：

```bash
browser-use open http://localhost:5173/
browser-use state
browser-use screenshot /tmp/scholarai-frontend-full-test/landing-root.png
browser-use open http://localhost:5173/home
browser-use state
browser-use screenshot /tmp/scholarai-frontend-full-test/landing-home.png
```

操作与预期：

1. 未登录点击 “开始探索”，预期进入 `/login`。
2. 登录后重新打开 `/`，点击 “开始探索”，预期进入 `/dashboard`。
3. 点击功能、技术、用户评价、支持按钮，预期页面滚动到对应 section。
4. 页面首屏中品牌、主 CTA、次 CTA 都可见且不被背景遮挡。

## 5.3 Login

代码入口：

1. `apps/web/src/app/pages/Login.tsx`

必须确认的 UI：

1. 登录模式与注册模式切换
2. 邮箱输入
3. 密码输入
4. 姓名输入
5. 终端日志区
6. 建立连接按钮
7. 模式切换按钮

必须测试的功能：

1. 已登录用户进入 `/login` 自动跳 `/dashboard`
2. 正常登录是否成功进入 `/dashboard`
3. 登录失败是否显示后端错误信息
4. 切到注册模式后是否显示注册字段
5. 注册成功后是否自动登录并进入 `/dashboard`

失败/边界：

1. 错误密码
2. 空输入
3. 注册接口失败
4. 文案中在线模型说明是否显示为在线主链

执行步骤：

```bash
browser-use open http://localhost:5173/login
browser-use state
```

操作与预期：

1. 输入固定账号密码，点击建立连接，预期进入 `/dashboard`。
2. 使用错误密码，预期停留登录页并显示错误信息。
3. 点击注册切换，预期出现姓名输入。
4. 刷新后终端日志区仍逐步显示初始化日志，不影响表单交互。
5. 文案显示在线 embedding / rerank / generation 主链，不出现本地模型默认文案。

## 5.4 Register

代码入口：

1. `apps/web/src/app/pages/Register.tsx`

必须确认的 UI：

1. 姓名、邮箱、密码、确认密码
2. 密码要求列表
3. 登录跳转入口

必须测试的功能：

1. 密码不一致时本地校验
2. 密码复杂度不达标时本地校验
3. 注册成功是否自动登录
4. 登录入口是否跳回 `/login`

执行步骤：

```bash
browser-use open http://localhost:5173/register
browser-use state
```

操作与预期：

1. 输入不匹配密码，预期显示“两次输入的密码不一致”。
2. 输入弱密码，预期显示密码不符合要求。
3. 输入新邮箱和合规密码，预期注册成功后进入 `/dashboard`。
4. 点击登录入口，预期进入 `/login`。

## 5.5 Forgot Password

代码入口：

1. `apps/web/src/app/pages/ForgotPassword.tsx`

必须确认的 UI：

1. 返回登录按钮
2. 邮箱输入
3. 发送按钮
4. 提交成功后的成功卡片

必须测试的功能：

1. 空邮箱拦截
2. 非法邮箱格式拦截
3. 成功提交后进入成功态
4. 成功态点击返回登录

执行步骤：

```bash
browser-use open http://localhost:5173/forgot-password
browser-use state
```

操作与预期：

1. 空邮箱提交，预期 toast 提示请输入邮箱。
2. 非法邮箱提交，预期 toast 提示邮箱格式不正确。
3. 合法邮箱提交，预期进入“重置链接已发送”成功态。
4. 点击返回登录，预期进入 `/login`。

## 5.6 Reset Password

代码入口：

1. `apps/web/src/app/pages/ResetPassword.tsx`

必须确认的 UI：

1. 新密码输入
2. 确认密码输入
3. 成功态卡片

必须测试的功能：

1. 无 `token` 时是否提示并回到 `/login`
2. 两次密码不一致拦截
3. 密码长度不足拦截
4. 成功重置后是否可返回登录

执行步骤：

```bash
browser-use open http://localhost:5173/reset-password
browser-use state
browser-use open "http://localhost:5173/reset-password?token=fake-token-for-ui-test"
browser-use state
```

操作与预期：

1. 无 token 访问，预期提示无效重置链接并回 `/login`。
2. 带 fake token 时输入短密码，预期本地拦截。
3. 输入两次不一致密码，预期本地拦截。
4. fake token 提交到后端失败时，预期显示重置失败，不出现页面崩溃。

## 5.7 Dashboard

代码入口：

1. `apps/web/src/app/pages/Dashboard.tsx`

必须确认的 UI：

1. 欢迎头部
2. command center 卡片
3. 空态三步引导
4. Search / Knowledge Base / Chat / Notes 快捷入口

必须测试的功能：

1. 有 command 数据时是否按优先级展示动作卡片
2. 无 command 数据时是否展示第一条研究链空态
3. 每张卡跳转是否落到正确页面
4. Dashboard 是否只做导航，不承担具体执行

现有覆盖：

1. `apps/web/src/features/workflow/commandCenter.test.ts`
2. `apps/web/src/features/workflow/hooks/useWorkflowHydration.test.tsx`

执行步骤：

```bash
browser-use open http://localhost:5173/dashboard
browser-use state
browser-use screenshot /tmp/scholarai-frontend-full-test/dashboard.png
```

操作与预期：

1. 首屏显示问候语和 command center。
2. 有 workflow command 时，卡片点击进入对应工作区。
3. 无 command 时，显示 Search / Add to KB / Ask in Chat 三步空态入口。
4. Dashboard 不直接执行上传、检索、对话，只跳转到对应页面。

## 5.8 Search

代码入口：

1. `apps/web/src/app/pages/Search.tsx`
2. `apps/web/src/features/search/components/SearchWorkspace.tsx`

子区域：

1. 左侧 `SearchSidebar`
2. 顶部 `SearchToolbar`
3. 结果区 `SearchResultsPanel`
4. 作者结果区 `SearchAuthorPanel`
5. 分页条 `SearchPagination`
6. KB 导入弹窗 `SearchKnowledgeBaseImportModal`
7. 右侧分析区
8. layered evidence 摘要区
9. planner metadata 区

必须确认的 UI：

1. 来源切换：`all` / `arxiv` / `s2` / `authors`
2. 查询输入与排序
3. 结果列表卡片
4. 分页条
5. 右侧来源统计、年份分布、作者分布
6. layered evidence 命中概览
7. 导入到 KB 弹窗

必须测试的功能：

1. 普通搜索 happy path
2. 翻页是否保留 query 与 sort
3. 作者搜索在少于 3 个字符时不触发
4. 结果卡片 “加入知识库” 是否能拉起导入流程
5. 结果卡片 “继续在 Chat 中问” 是否 handoff 成功
6. 从结果点开阅读页是否带 `page` 与 `source_id`
7. 搜索结果为空时是否显示正确 empty 文案
8. 部分外部源失败时是否显示 degraded 文案但仍保留可用结果

现有覆盖：

1. `apps/web/src/app/pages/Search.test.tsx`
2. `apps/web/src/features/search/hooks/useSearchImportFlow.test.tsx`
3. `apps/web/src/features/search/components/SearchKnowledgeBaseImportModal.test.tsx`
4. `apps/web/src/features/search/components/SearchResultsPanel.test.tsx`
5. `apps/web/e2e/retrieval-critical.spec.ts`
6. `apps/web/e2e/search-pagination-stability.spec.ts`

建议补充：

1. `authors` 模式完整交互 E2E
2. `layeredEvidence` 面板可视回归
3. query param 恢复测试

执行步骤：

```bash
browser-use open "http://localhost:5173/search"
browser-use state
```

操作与预期：

1. 在查询框输入 `large language model retrieval` 并提交，预期结果区出现论文结果或明确 empty/degraded 状态。
2. 切换 `all`、`arxiv`、`s2`，预期结果来源和状态行同步变化。
3. 切换 `authors`，输入少于 3 字符，预期不触发作者列表；输入 `Hinton`，预期出现作者结果或明确 empty 状态。
4. 点击分页下一页和上一页，预期 URL/page 状态和结果区稳定。
5. 对一条有 `paperId` 的结果点击继续 Chat，预期进入 `/chat?paperId=...&handoff=1&new=1` 或等价 handoff 状态，composer 被预填。
6. 对一条可导入结果点击加入知识库，预期打开 KB 选择弹窗。
7. 选择测试知识库并确认导入，预期跳到 KB 或显示导入状态。

记录项：

1. `search-results.png`
2. `search-author-mode.png`
3. `search-import-modal.png`
4. `search-chat-handoff.png`

## 5.9 Knowledge Base List

代码入口：

1. `apps/web/src/app/pages/KnowledgeBaseList.tsx`

子区域：

1. 顶部工具栏
2. 创建知识库弹窗
3. 右侧 inspector
4. 卡片视图
5. 表格视图
6. 批量模式
7. 行级 dropdown 菜单
8. ImportDialog

必须确认的 UI：

1. 搜索框
2. 分类标签筛选
3. 排序切换
4. 卡片/列表视图切换
5. 批量模式切换
6. 存储统计
7. 最近知识库 inspector

必须测试的功能：

1. 创建知识库
2. 搜索、分类、排序是否联动 URL 状态
3. 卡片视图与表格视图切换
4. 单个知识库进入详情页
5. 单个知识库导入来源
6. 重命名知识库
7. 删除知识库
8. 批量勾选与批量删除
9. 右侧 inspector 开关

失败/边界：

1. 存储统计加载失败
2. 批量删除失败
3. 空列表状态

执行步骤：

```bash
browser-use open "http://localhost:5173/knowledge-bases"
browser-use state
browser-use screenshot /tmp/scholarai-frontend-full-test/kb-list.png
```

操作与预期：

1. 点击创建知识库，填写 `frontend-full-test-YYYYMMDD-HHMM`，确认后预期列表出现新知识库。
2. 搜索新知识库名称，预期只展示匹配项，刷新后搜索 query 保持。
3. 切换卡片/列表视图，预期同一数据以不同布局展示。
4. 切换排序，预期 URL 或列表顺序同步变化。
5. 开启批量模式，勾选一个测试 KB，预期批量 action bar 出现。
6. 打开行级菜单，逐项确认“进入知识库 / 导入来源 / 编辑 / 删除”可见。
7. 点击进入知识库，预期进入 `/knowledge-bases/:id`。

记录项：

1. `kb-list-card.png`
2. `kb-list-table.png`
3. `kb-list-batch-mode.png`

## 5.10 Knowledge Base Detail

代码入口：

1. `apps/web/src/app/pages/KnowledgeBaseDetail.tsx`
2. `apps/web/src/features/kb/components/KnowledgeWorkspaceShell.tsx`

子页面 / tabs：

1. `papers`
2. `import-status`
3. `uploads`
4. `search`
5. `runs`
6. `review`
7. `chat`

顶部功能区：

1. 返回知识库列表
2. 上传工作台
3. 导入来源
4. 对整个知识库提问
5. readiness 卡片

必须确认的 UI：

1. KB 名称、模型、引擎、paper/chunk 计数
2. readiness 卡片是否显示状态与原因
3. tab 切换后主区块是否切换

必须测试的功能：

1. `tab` query param 是否驱动 active tab
2. Refresh 是否重新拉取 KB / papers / import jobs / runs
3. 导入过程中 polling 是否生效
4. readiness 卡点击是否跳到正确目标页面
5. 顶部 “对整个知识库提问” 是否跳到 `/chat?kbId=...`

执行步骤：

```bash
browser-use open "http://localhost:5173/knowledge-bases/<kb_id>"
browser-use state
browser-use screenshot /tmp/scholarai-frontend-full-test/kb-detail-overview.png
```

通用通过标准：

1. 顶部显示 KB 名称、模型、引擎、paper/chunk 计数。
2. `Readiness` 卡片显示状态和下一步目标。
3. 每个 tab 点击后 URL `tab` 参数和内容同步。
4. Refresh 后数据不会清空或退回错误态。

### 5.10.1 papers tab

必须测试：

1. 论文列表加载
2. 导入完成后是否高亮新论文
3. 论文为空时空态
4. 从论文进入阅读页

执行步骤：

```bash
browser-use open "http://localhost:5173/knowledge-bases/<kb_id>?tab=papers"
browser-use state
```

预期结果：

1. 已上传 PDF 对应论文出现在列表中。
2. 论文卡片/行点击可进入 `/read/:paperId`。
3. 新导入论文如果带 state，高亮只影响当前目标，不污染其他论文。

### 5.10.2 import-status tab

必须测试：

1. ImportJob 状态流展示
2. 完成后是否触发派生数据刷新
3. `created / running / awaiting_user_action / completed / failed` 视觉状态

执行步骤：

```bash
browser-use open "http://localhost:5173/knowledge-bases/<kb_id>?tab=import-status"
browser-use state
```

预期结果：

1. 最近 import job 可见。
2. 运行中 job 显示 running/awaiting 状态。
3. 完成 job 后 KB paper/chunk 计数刷新。
4. 失败 job 显示后端失败原因、可重试入口或明确 next action。
5. 不允许出现 `0 Chunks / Pending index` 与 search 已返回 evidence 的矛盾状态；若出现，记录为 backend/data contract 缺口。
6. 上传解析完成后 SQL `paper_chunks`、Milvus evidence、KB header 计数三者必须一致。

### 5.10.3 uploads tab

必须测试：

1. 拖拽 PDF
2. 文件选择 PDF
3. 非 PDF 过滤
4. 队列删除
5. 开始上传
6. 全成功、部分成功、全失败三类 toast
7. `onQueueComplete` 是否刷新 KB 状态

执行步骤：

```bash
browser-use open "http://localhost:5173/knowledge-bases/<kb_id>?tab=uploads"
browser-use state
# 找到 file input 或“点击选择文件”对应元素后：
browser-use upload <file_input_index> apps/api/tests/fixtures/pdfs/test_5_pages.pdf
browser-use state
# 找到“开始上传”按钮后：
browser-use click <start_upload_index>
browser-use state
```

预期结果：

1. 文件进入上传队列。
2. 点击开始上传后按钮进入上传中。
3. 成功提交后显示成功 toast。
4. `import-status` tab 可看到对应 job。
5. 等待 worker 完成后 `papers` 和 `chunks` 计数增加。

失败记录必须区分：

1. 前端未选中文件：frontend
2. upload API 失败：backend
3. worker 未解析/未索引：backend/data
4. browser-use upload index 失效：tooling

### 5.10.4 search tab

必须测试：

1. KB 内检索是否返回证据结果
2. 点击结果是否打开 `/read/:paperId?page=:n&source=evidence&source_id=:chunk`
3. 无论文时是否提示 papers empty
4. evidence 卡 key 稳定性

现有覆盖：

1. `apps/web/src/features/kb/hooks/useKnowledgeBaseSearch.test.tsx`
2. `apps/web/src/features/kb/components/KnowledgeWorkspaceShell.test.tsx`

执行步骤：

```bash
browser-use open "http://localhost:5173/knowledge-bases/<kb_id>?tab=search"
browser-use state
# 输入 method / results / introduction
browser-use input <kb_search_input_index> "method"
browser-use click <kb_search_button_index>
browser-use state
browser-use screenshot /tmp/scholarai-frontend-full-test/kb-search-results.png
```

预期结果：

1. 返回 evidence 结果列表。
2. 每条结果包含论文标题、片段、页码或来源信息。
3. 点击结果进入 `/read/:paperId?page=...&source=evidence&source_id=...`。
4. Read 页面出现 source highlight 或 evidence sidenote。
5. evidence 卡没有 React duplicate key 警告。
6. summary 命中也必须映射到 representative source chunk，不能跳到不存在的 source id。

### 5.10.5 runs tab

必须测试：

1. runs 列表加载
2. 点击 run 是否进入 `?tab=review&runId=...`

执行步骤：

```bash
browser-use open "http://localhost:5173/knowledge-bases/<kb_id>?tab=runs"
browser-use state
```

预期结果：

1. 无 runs 时显示空态。
2. 有 runs 时显示列表。
3. 点击 run 后 URL 变为 `?tab=review&runId=<run_id>`。

### 5.10.6 review tab

必须测试：

1. draft 列表加载
2. create draft
3. retry draft
4. claim repair
5. claim evidence 跳转阅读页
6. continue in chat handoff
7. `runId` query param 恢复

执行步骤：

```bash
browser-use open "http://localhost:5173/knowledge-bases/<kb_id>?tab=review"
browser-use state
```

预期结果：

1. Review Draft 面板加载。
2. 选择论文后可创建 draft。
3. draft 的 claim/evidence 列表可见。
4. evidence 跳转进入 Read 并带 `source_id`。
5. continue in Chat 进入 KB scoped handoff。
6. draft partial / insufficient evidence 必须诚实显示，不可伪装成全通过。

### 5.10.7 chat tab

必须测试：

1. Quick Ask 面板展示 KB 作用域
2. 进入 KB 范围 Chat

执行步骤：

```bash
browser-use open "http://localhost:5173/knowledge-bases/<kb_id>?tab=chat"
browser-use state
```

预期结果：

1. Quick Ask 显示当前 `kb_id`。
2. 点击进入 Chat 后 URL 包含 `kbId=<kb_id>`。
3. Chat scope banner 显示整库作用域。

现有覆盖：

1. `apps/web/src/app/pages/KnowledgeBaseDetail.test.tsx`
2. `apps/web/src/app/pages/KnowledgeBaseDetail.shell.test.tsx`
3. `apps/web/src/features/kb/components/KnowledgeBaseDetailV2.test.tsx`
4. `apps/web/src/features/kb/components/KnowledgeReviewPanel.test.tsx`
5. `apps/web/src/features/kb/hooks/useImportJobsPolling.test.tsx`
6. `apps/web/src/features/kb/hooks/useKnowledgeBaseQueries.test.tsx`
7. `apps/web/src/features/kb/hooks/useKnowledgeBaseWorkspace.test.tsx`
8. `apps/web/src/features/kb/hooks/useKnowledgeRuns.test.tsx`
9. `apps/web/src/features/kb/hooks/useKnowledgeWorkflowRefresh.test.tsx`
10. `apps/web/e2e/kb-critical.spec.ts`
11. `apps/web/e2e/pr19-stepwise-flow.spec.ts`

## 5.11 Read

代码入口：

1. `apps/web/src/app/pages/Read.tsx`

子区域：

1. 顶部工具栏
2. 左侧章节树
3. 中央 PDF viewer
4. 底部缩略图条
5. 右侧面板
6. 右侧 tabs：`notes` / `annotations` / `summary`
7. `SourceChunkHighlight`
8. `EvidenceSideNote`

必须确认的 UI：

1. 无 `id` 时空态
2. 有 `id` 时三栏布局
3. 页码输入、翻页按钮、缩放、全屏、右侧面板开关
4. 章节树
5. 缩略图条
6. 注释列表
7. AI 总结区
8. 阅读笔记区

必须测试的功能：

1. `?page=` 是否驱动当前页
2. 刷新后页码是否保留
3. 阅读进度是否保存
4. 章节树点击跳页
5. 缩略图点击跳页
6. 从搜索/聊天/KB 证据跳来时 `source_id` 是否高亮
7. `source=chat|search|evidence` 时右侧默认 tab 是否正确
8. “继续在 Chat 中问” 是否带当前 paper/page/source 进入 handoff
9. 注释创建后列表是否刷新
10. 阅读笔记是否自动保存
11. “插入当前页引用” 是否写入 `[[pdf:paperId:page:n]]`
12. “在笔记页编辑” 是否跳到 `/notes?paperId=...&noteId=...`

失败/边界：

1. 论文加载失败
2. 阅读进度保存失败提示
3. 无 summary / 无 annotation / 无 note 的空态
4. 右侧面板 resize 边界

建议重点回归：

1. `KB search -> Read -> highlight`
2. `Chat citation -> Read -> highlight`
3. `Notes pdf ref -> Read?page=n`

执行步骤：

```bash
browser-use open "http://localhost:5173/read"
browser-use state
browser-use open "http://localhost:5173/read/<paper_id>?page=1&source=evidence&source_id=<source_chunk_id>"
browser-use state
browser-use screenshot /tmp/scholarai-frontend-full-test/read-highlight.png
```

操作与预期：

1. `/read` 空工作台显示“选择一篇论文开始沉浸阅读”，CTA 可进入 KB 和 Search。
2. `/read/:id?page=1` 加载 PDF viewer、章节树、缩略图条和右侧面板。
3. 修改页码输入并回车，预期 URL `page` 更新并保存阅读进度。
4. 点击下一页/上一页，预期页码和 PDF 视图同步。
5. 点击章节树节点，预期跳到对应页。
6. 点击缩略图，预期跳到对应页。
7. 点击右侧 `notes`、`annotations`、`summary` tab，预期内容切换且不丢失当前页。
8. `source_id` 存在时，预期显示 source highlight 或 evidence sidenote。
9. 点击“继续问”，预期进入 Chat，composer 预填，handoff evidence 带当前 paper/page/source。
10. 在 notes tab 输入内容，等待 autosave，预期显示已保存。
11. 点击“插入当前页引用”，预期 note 内容增加 `[[pdf:<paper_id>:page:<n>]]`。
12. 点击“在笔记页编辑”，预期进入 `/notes?paperId=<paper_id>`，如存在 note 则带 `noteId`。

记录项：

1. `read-empty.png`
2. `read-pdf-loaded.png`
3. `read-highlight.png`
4. `read-notes-saved.png`

失败判定：

1. PDF 不显示但 API 成功：frontend/PDF viewer
2. paper API 404 或 500：backend/data
3. source highlight 缺失但 URL 有 `source_id`：frontend/backend contract
4. notes 保存失败：backend/notes API 或 frontend autosave

## 5.12 Chat

代码入口：

1. `apps/web/src/app/pages/Chat.tsx`
2. `apps/web/src/features/chat/workspace/ChatWorkspaceV2.tsx`

这是前端测试最高优先级页面，必须单独做深测。

Chat 执行前准备：

1. 至少有一个已完成索引的 `paper_id`。
2. 至少有一个有 chunks 的 `kb_id`。
3. 至少有一个 evidence `source_chunk_id`，可从 KB search 或 Chat citation 中获得。
4. 后端 generation 必须为在线模型链路；若回答失败，先看 API/worker 日志，不把所有失败归给前端。
5. 至少执行三类问题：通用聊天、单论文 RAG、整库 KB RAG。
6. 如果回答是 abstain / partial，先确认 paper chunks、scope query、retrieval trace 与 evidence payload，再判定是后端检索不足、数据不足还是前端渲染错误。
7. Chat 页面必须记录当前 scope banner 文案，避免“看似在问论文，实际无 paper/kb scope”的假阳性。

基础打开步骤：

```bash
browser-use open "http://localhost:5173/chat"
browser-use state
browser-use screenshot /tmp/scholarai-frontend-full-test/chat-empty.png
```

基础通过标准：

1. Chat workspace 可见。
2. session 列表或空态可见。
3. composer 可输入。
4. right panel 可开合。
5. 没有无限 loading。
6. 发送后消息不会被旧 session hydration 覆盖。
7. streaming 期间 composer lock、停止/重试按钮、消息追加顺序稳定。
8. 线上 generation 失败时显示错误 contract，不白屏、不吞消息。

### 5.12.1 UI 区域

1. 顶部 `RunHeader`
2. `WorkflowShell`
3. scope banner
4. 左侧 session sidebar
5. message feed
6. composer
7. right panel
8. evidence / citation / reasoning / tool timeline
9. confirmation dialogs

### 5.12.2 路由与 query param 矩阵

必须覆盖：

1. `/chat`
2. `/chat?new=1`
3. `/chat?session=:id`
4. `/chat?paperId=:id`
5. `/chat?kbId=:id`
6. `/chat?paper_ids=a,b,c`
7. `handoff=1`
8. `paperId` 与 `kbId` 共存错误态

必须确认：

1. `new=1` 触发一次性新会话流程
2. `session` 切换目标会话
3. `paperId` 进入单论文 scope
4. `kbId` 进入整库 scope
5. `paper_ids` 进入 compare scope
6. handoff 数据只 hydrate 一次，不重复覆盖 composer

执行步骤：

```bash
browser-use open "http://localhost:5173/chat?new=1"
browser-use state
browser-use open "http://localhost:5173/chat?paperId=<paper_id>"
browser-use state
browser-use open "http://localhost:5173/chat?kbId=<kb_id>"
browser-use state
browser-use open "http://localhost:5173/chat?paper_ids=<paper_id_1>,<paper_id_2>"
browser-use state
browser-use open "http://localhost:5173/chat?paperId=<paper_id>&kbId=<kb_id>"
browser-use state
```

预期结果：

1. `new=1` 后 composer 为空、当前会话清空，URL 中 `new` 被消费或进入新会话状态。
2. `paperId` 显示单论文 scope。
3. `kbId` 显示整库 scope。
4. `paper_ids` 显示 compare scope。
5. `paperId + kbId` 显示非法作用域告警，不应默默选择其中一个。

### 5.12.3 会话生命周期

必须测试：

1. 新建会话
2. 会话列表展示
3. 会话搜索
4. 切换会话
5. 删除会话
6. 删除确认弹窗
7. URL `session` 与当前会话同步
8. 不同会话消息隔离

执行步骤：

```bash
browser-use open "http://localhost:5173/chat?new=1"
browser-use state
# 输入并发送第一条短消息
browser-use input <composer_index> "用一句话说明你能做什么。"
browser-use click <send_index>
browser-use state
```

预期结果：

1. 发送后出现用户消息。
2. 出现 assistant placeholder 或 streaming 状态。
3. 完成后 URL 包含 `session=<id>` 或 session 列表出现新会话。
4. 点击新对话后旧消息不显示。
5. 点击旧会话后旧消息恢复。
6. 删除会话需要确认，确认后列表移除。

### 5.12.4 发送与流式响应

必须测试：

1. 输入消息发送
2. 重复点击发送防抖
3. placeholder message 创建
4. `message_id` 与 placeholder 绑定
5. streaming token 持续追加
6. reasoning 与 content 缓冲分离
7. `done` 收束
8. `error` 收束
9. `cancelled` 收束
10. stop 按钮中止
11. 完成后消息持久化回 session

必须验证的协议点：

1. 每个 SSE event 都正确落到当前 `message_id`
2. 旧 stream 的事件不会污染新消息
3. 已完成或已错误的消息不再吃 streaming patch
4. placeholder 清理与真实消息替换一致

执行步骤：

```bash
browser-use open "http://localhost:5173/chat?new=1"
browser-use state
browser-use input <composer_index> "总结一下 RAG 回答应该如何引用证据。"
browser-use click <send_index>
browser-use state
# streaming 中截屏
browser-use screenshot /tmp/scholarai-frontend-full-test/chat-streaming.png
# 等待回答完成后
browser-use state
browser-use screenshot /tmp/scholarai-frontend-full-test/chat-answer-complete.png
```

预期结果：

1. 发送按钮在 streaming 中防重复。
2. assistant 消息逐步更新或显示稳定 loading。
3. 完成后不再显示 streaming spinner。
4. 消息内容不重复、不覆盖用户消息。
5. 右侧 run/token/tool 状态若有数据，应和当前消息对应。
6. 浏览器 console 不出现重复 key、hook crash、undefined property crash。

中断测试：

1. 发送长问题后点击 stop。
2. 预期当前消息进入 cancelled 或停止态。
3. 再发送新问题，预期新回答不吃旧回答残留。

### 5.12.5 scope 与 handoff

必须测试：

1. Search -> Chat handoff
2. Read -> Chat handoff
3. Review -> Chat handoff
4. Compare -> Chat handoff
5. KB -> Chat handoff
6. returnTo 保留
7. evidence 引用数量显示
8. promptDraft 是否预填到 composer 但不自动发送

执行步骤：

1. 从 Search 结果点击继续 Chat。
2. 从 Read 点击继续问。
3. 从 KB chat tab 点击进入 Chat。
4. 从 Compare 点击 Continue in Chat。
5. 从 Review draft 点击 Continue in Chat。

预期结果：

1. URL 包含对应 scope query。
2. composer 有 promptDraft。
3. promptDraft 不自动发送。
4. handoff banner 显示来源。
5. evidence count 与来源页面传入数量一致。
6. 刷新后 durable handoff 能恢复一次。
7. 修改 composer 后，不会被 handoff 再次覆盖。

### 5.12.6 证据、引用与跳转

必须测试：

1. citation panel 渲染
2. inline citation 点击
3. evidence panel 列表渲染
4. compare response card 渲染
5. compare card 跳去 `/compare?paper_ids=...`
6. evidence block 跳阅读页时 `source_id` 和 `page` 是否正确
7. `source_chunk_id`、`source_id`、`chunk_id` fallback 映射

执行步骤：

```bash
browser-use open "http://localhost:5173/chat?paperId=<paper_id>&new=1"
browser-use state
browser-use input <composer_index> "这篇论文的方法部分有哪些关键证据？请给出引用。"
browser-use click <send_index>
browser-use state
```

预期结果：

1. 回答包含 citation 或 evidence block。
2. inline citation 可点击。
3. Evidence panel 中 source chunk link 可点击。
4. 点击后进入 `/read/<paper_id>?page=<n>&source=chat&source_id=<chunk>`。
5. Read 页面显示对应 source highlight。
6. 如果回答没有 citation，必须区分：证据不足导致诚实回答、后端没有返回 evidence、前端没有渲染 evidence。
7. evidence block 中的 `paper_id`、`page`、`source_chunk_id` 与 Read URL 保持一致。

整库 RAG 测试：

```bash
browser-use open "http://localhost:5173/chat?kbId=<kb_id>&new=1"
browser-use state
browser-use input <composer_index> "这个知识库里的论文主要研究什么问题？请基于证据回答。"
browser-use click <send_index>
browser-use state
```

预期结果：

1. 回答基于 KB evidence。
2. 不应假性 abstain，除非 KB 确实没有 chunks。
3. 引用跳转可用。
4. KB scope banner 与 `kbId` 一致。
5. 如果命中 summary result，仍可跳转到代表性 chunk 对应的 Read 高亮。

Compare response 测试：

```bash
browser-use open "http://localhost:5173/chat?paper_ids=<paper_id_1>,<paper_id_2>&new=1"
browser-use state
browser-use input <composer_index> "对比这两篇论文的方法、贡献和局限。"
browser-use click <send_index>
browser-use state
```

预期结果：

1. 如果后端返回 `response_type=compare`，前端显示 CompareCard。
2. `View full table` 进入 `/compare?paper_ids=...`。
3. 不支持 compare 时必须显示清楚错误或普通回答，不可白屏。

### 5.12.7 右侧面板与运行态

必须测试：

1. reasoning panel 展开/收起
2. tool timeline 渲染
3. token / cost / run 状态展示
4. right panel 开关
5. 选中消息后右侧面板内容同步

执行步骤：

1. 打开 right panel。
2. 发送一条问题。
3. 等待 tool timeline / reasoning / citations 有内容。
4. 点击不同消息。

预期结果：

1. right panel 开关不改变消息内容。
2. 选中消息后 panel 显示当前消息相关信息。
3. 无工具调用时显示空态，不崩溃。
4. 长 tool event 不挤压 composer。

### 5.12.8 失败与恢复

必须测试：

1. SSE 中断
2. 后端返回 error contract
3. 用户取消
4. handoff 持久化对象损坏
5. 切会话时流式消息未完成
6. 作用域 query 非法组合

执行步骤：

1. 网络面板或后端临时中断时发送消息。
2. 观察错误提示。
3. 恢复服务后再次发送。

预期结果：

1. 错误不会导致页面白屏。
2. send lock 被释放。
3. 新消息可以继续发送。
4. 旧错误消息仍留在对话历史中或清楚标记失败。

### 5.12.9 响应式

必须测试：

1. 手机宽度下 session sidebar 可用性
2. composer 固定与滚动行为
3. pinned bottom 行为
4. 长消息、长 citation、长会话标题不溢出

执行步骤：

```bash
# browser-use CLI 无固定 viewport 命令时，使用 Playwright 或 in-app browser 手动设置 390x844。
browser-use open "http://localhost:5173/chat"
browser-use state
```

预期结果：

1. 移动端可打开导航。
2. composer 不被底部遮挡。
3. 长回答可滚动。
4. citation/CompareCard 不横向破版。
5. session 搜索可用。

### 5.12.10 Chat 页现有自动化覆盖

单测/组件：

1. `apps/web/src/app/pages/Chat.test.tsx`
2. `apps/web/src/features/chat/workspace/ChatWorkspaceV2.test.tsx`
3. `apps/web/src/features/chat/hooks/useChatSend.test.tsx`
4. `apps/web/src/features/chat/hooks/useChatRun.test.tsx`
5. `apps/web/src/features/chat/hooks/useChatRuntimeBridge.test.ts`
6. `apps/web/src/features/chat/hooks/useChatScopeController.test.ts`
7. `apps/web/src/features/chat/hooks/useChatSessionController.test.ts`
8. `apps/web/src/features/chat/hooks/usePinnedBottom.test.tsx`
9. `apps/web/src/features/chat/chatHandoff.test.ts`
10. `apps/web/src/features/chat/chatHandoff.session-isolation.test.ts`
11. `apps/web/src/features/chat/adapters/sseEventAdapter.test.ts`
12. `apps/web/src/features/chat/components/message-feed/MessageFeed.test.tsx`
13. `apps/web/src/features/chat/components/evidence/EvidencePanel.test.tsx`
14. `apps/web/src/features/chat/components/citation-panel/CitationPanel.test.tsx`
15. `apps/web/src/features/chat/components/session-sidebar/SessionSidebar.test.tsx`
16. `apps/web/src/features/chat/components/CompareCard.test.tsx`

E2E：

1. `apps/web/e2e/chat-critical.spec.ts`
2. `apps/web/e2e/chat-evidence.spec.ts`
3. `apps/web/e2e/chat-responsive.spec.ts`
4. `apps/web/e2e/chat-session-search.spec.ts`
5. `apps/web/e2e/user-journey.spec.ts`

### 5.12.11 Chat 页建议新增回归

1. `new=1` 与 handoff 同时出现的一次性恢复测试
2. `paperId + kbId` 非法组合的 UI 告警测试
3. compare scope 下 follow-up 问题继续带 `paper_ids` 的 E2E
4. 流式中切会话的稳定性 E2E
5. 取消后再次发送的新旧 stream 隔离测试

## 5.13 Notes

代码入口：

1. `apps/web/src/app/pages/Notes.tsx`

子区域：

1. 左侧笔记库面板
2. 文件夹树
3. 搜索框
4. 标签筛选
5. 系统摘要区
6. 用户笔记列表
7. 编辑器区
8. linked evidence 区
9. 删除确认弹窗

必须确认的 UI：

1. 文件夹先行工作流
2. 自动生成的 KB 文件夹
3. 手动文件夹
4. 用户笔记与系统摘要分区
5. 编辑器保存状态

必须测试的功能：

1. `paperId` query param 过滤
2. `noteId` query param 恢复
3. 未选文件夹时创建笔记拦截
4. 创建文件夹
5. 创建笔记
6. 自动保存
7. 标题编辑
8. 删除笔记
9. 标签筛选与全文搜索
10. 系统摘要转为用户笔记
11. 系统摘要追加到当前笔记
12. 从 notes 打开阅读页
13. 插入论文引用
14. linked evidence 展示

现有覆盖：

1. `apps/web/src/features/notes/ownership.test.ts`
2. `apps/web/e2e/notes-rendering.spec.ts`

建议补充：

1. `paperId/noteId` URL 恢复 Vitest 页面测试
2. autosave 失败重试测试
3. KB 文件夹与手动文件夹混合场景测试

执行步骤：

```bash
browser-use open "http://localhost:5173/notes"
browser-use state
browser-use screenshot /tmp/scholarai-frontend-full-test/notes-home.png
```

操作与预期：

1. 无选中文件夹时点击新建，预期 toast 提示先选择文件夹。
2. 创建手动文件夹，预期文件夹树出现新文件夹。
3. 选择文件夹后点击新建，预期创建用户笔记并选中。
4. 编辑标题，预期 blur 后保存。
5. 输入正文，等待 autosave，预期保存状态变为已保存。
6. 搜索关键词，预期列表过滤并高亮命中。
7. 如果有 `paperId`，打开 `/notes?paperId=<paper_id>`，预期自动过滤该论文相关笔记/摘要。
8. 如果有 `noteId`，打开 `/notes?paperId=<paper_id>&noteId=<note_id>`，预期自动选中对应 note。
9. 点击系统摘要的“转为笔记”，预期生成用户可编辑笔记。
10. 点击系统摘要的“加入当前笔记”，预期当前笔记追加摘要内容。
11. 点击“打开阅读页”，预期进入 `/read/<paper_id>?source=notes`。
12. 删除笔记时必须出现确认弹窗，取消不删除，确认后列表移除。

记录项：

1. `notes-folder-tree.png`
2. `notes-editor-saved.png`
3. `notes-paper-filter.png`
4. `notes-delete-confirm.png`

## 5.14 Compare

代码入口：

1. `apps/web/src/app/pages/Compare.tsx`

子区域：

1. 论文搜索与选择区
2. 已选论文 chip 区
3. 维度选择区
4. 研究问题输入
5. compare matrix 主区
6. cross-paper insights 区
7. Save to Notes
8. Continue in Chat

必须确认的 UI：

1. 论文搜索输入与结果下拉
2. 2-10 篇论文选择约束
3. 维度 toggle 列表
4. 运行 compare 按钮
5. matrix 表
6. 每个 cell 的 evidence / save / chat 操作

必须测试的功能：

1. 从 `paper_ids` query param 恢复已选论文
2. 不足 2 篇时不能 compare
3. 超过 10 篇时拦截
4. compare 成功后渲染 matrix
5. cell evidence 跳转阅读页
6. cell continue in chat 带 compare handoff
7. 保存 compare 到 notes
8. 顶部 continue in chat 带整组论文与问题
9. cross-paper insights 渲染

现有覆盖：

1. `apps/web/e2e/compare-critical.spec.ts`
2. `apps/web/src/features/chat/components/CompareCard.test.tsx`
3. `apps/web/src/features/chat/hooks/useChatSend.test.tsx`

执行步骤：

```bash
browser-use open "http://localhost:5173/compare"
browser-use state
```

操作与预期：

1. 未选择论文时，Compare 按钮不可执行或显示不足 2 篇限制。
2. 搜索论文关键词，预期出现结果。
3. 添加 2 篇论文，预期 chip 区显示 2/10。
4. 关闭某个维度 toggle，预期 matrix 请求只带启用维度。
5. 输入研究问题。
6. 点击运行对比，预期 loading 后显示 compare matrix。
7. 点击 cell 的 `p.<n>` evidence，预期进入 Read 并带 source。
8. 点击 cell 的 Save，预期保存 evidence 到 Notes。
9. 点击 cell 的 Chat，预期进入 compare scoped Chat handoff。
10. 点击顶部 Save to Notes，预期生成 compare note。
11. 点击顶部 Continue in Chat，预期进入 `/chat?paper_ids=...&handoff=1&new=1`。
12. 直接打开 `/compare?paper_ids=<paper_id_1>,<paper_id_2>`，预期自动恢复已选论文。

记录项：

1. `compare-selection.png`
2. `compare-matrix.png`
3. `compare-chat-handoff.png`

## 5.15 Analytics

代码入口：

1. `apps/web/src/app/pages/Analytics.tsx`

子区域：

1. summary cards
2. latest offline gate
3. recent runs 列表
4. mode filter
5. selected run detail
6. family chart
7. diff report

必须确认的 UI：

1. 刷新按钮
2. 空态
3. 错误态
4. latest gate 卡
5. recent runs
6. diff 区

必须测试的功能：

1. 拉 overview 成功
2. 自动选择 latest offline gate run
3. mode filter 切换
4. 点击 run 查看详情
5. 运行 diff
6. gate failures 展示

现有覆盖：

1. `apps/web/src/app/pages/Analytics.test.tsx`

执行步骤：

```bash
browser-use open "http://localhost:5173/analytics"
browser-use state
browser-use screenshot /tmp/scholarai-frontend-full-test/analytics.png
```

操作与预期：

1. 页面加载时显示 loading，完成后显示 overview 或空态。
2. 点击 Refresh，预期重新加载且按钮 spinner 不会卡死。
3. 切换 `all / offline / online`，预期 recent runs 过滤。
4. 点击某个 run，预期 detail、family chart 和指标表更新。
5. 点击 diff，预期出现 improved/regressed/unchanged 汇总。
6. 无 eval 数据时显示明确空态，不白屏。
7. API 失败时显示错误态和重试入口。

## 5.16 Settings

代码入口：

1. `apps/web/src/app/pages/Settings.tsx`

子区域：

1. Profile
2. Localization
3. Display
4. Security
5. API
6. Diagnostics
7. 左侧 sidebar
8. 右侧 status rail

必须确认的 UI：

1. section 切换
2. 当前 section 标题与版本标签
3. profile form
4. 语言切换按钮
5. 字号选择器
6. logout 区块
7. API key manager
8. diagnostics 面板

必须测试的功能：

1. section 切换是否正确渲染
2. 语言切换是否立即生效
3. 字号切换是否写入 store
4. logout 确认弹窗与实际登出
5. diagnostics 只读展示是否正常

现有覆盖：

1. `apps/web/src/app/pages/Settings.test.tsx`

执行步骤：

```bash
browser-use open "http://localhost:5173/settings"
browser-use state
browser-use screenshot /tmp/scholarai-frontend-full-test/settings-profile.png
```

操作与预期：

1. 点击 Profile，预期 ProfileForm 出现。
2. 点击 Localization，切换 English / 中文，预期页面文案随语言变化。
3. 点击 Display，切换字号，预期字体大小配置写入 store，刷新后保持。
4. 点击 Security，点击 Logout，预期确认弹窗出现；取消后仍在 settings；确认后回 `/login`。
5. 点击 API，预期 APIKeyManager 出现。
6. 点击 Diagnostics，预期 SystemDiagnostics 出现。
7. 右侧 status rail 不遮挡主内容。
8. API key manager 若后端能力开启，新增、复制、隐藏、撤销、空态和错误态都必须可操作；若未开启，必须显示清楚不可用原因。
9. Diagnostics 中 API、auth、storage、模型 provider 状态应与 `/api/v1/system/health` 或后端健康接口一致。
10. 线上模型信息不允许显示本地 BGE/Qwen 加载态；若出现，记录为 runtime provider regression。

## 5.17 /workspace 重定向

代码入口：

1. `apps/web/src/app/routes.tsx`

必须测试：

1. 登录态进入 `/workspace` 是否 302/重定向到 `/dashboard`
2. 未登录进入 `/workspace` 是否最终回 `/login`

执行步骤：

```bash
browser-use open "http://localhost:5173/workspace"
browser-use state
```

预期结果：

1. 登录态最终进入 `/dashboard`。
2. 清 cookie 后进入 `/workspace`，最终进入 `/login`。

## 5.18 /read 空工作台

代码入口：

1. `apps/web/src/app/pages/Read.tsx`

必须测试：

1. 直接进入 `/read` 时空工作台是否可用
2. 空工作台 CTA 是否跳去 `/knowledge-bases` 与 `/search`

执行步骤：

```bash
browser-use open "http://localhost:5173/read"
browser-use state
```

预期结果：

1. 页面显示阅读空态。
2. 点击前往知识库，进入 `/knowledge-bases`。
3. 返回 `/read` 后点击前往检索，进入 `/search`。

## 6. 建议执行清单

建议把前端全量测试拆成四轮：

1. 路由与壳层轮：
   - Landing
   - Auth pages
   - Layout
   - `/workspace` redirect
2. 研究主链轮：
   - Search
   - Knowledge Base List
   - Knowledge Base Detail 全部 tabs
   - UploadWorkspace
3. 阅读与沉淀轮：
   - Read
   - Notes
   - Compare
4. 高优先智能交互轮：
   - Chat
   - Analytics
   - Settings

## 6.1 可执行总表

| order | route/surface | prerequisite | action summary | pass evidence |
|---|---|---|---|---|
| 1 | `/` and `/home` | none | open, CTA, anchors | landing screenshots |
| 2 | `/login` | fixed account | login success and failure | dashboard URL |
| 3 | `/register` | throwaway email | validation and optional registration | validation screenshots |
| 4 | `/forgot-password` | any email | invalid/valid email flow | success card |
| 5 | `/reset-password` | fake token | local validation and API failure | no crash |
| 6 | `Layout` | login | nav, collapse, recent sessions, logout | layout screenshots |
| 7 | `/dashboard` | login | command cards and empty-state links | dashboard screenshot |
| 8 | `/search` | login | search, source modes, import, chat handoff | search screenshots |
| 9 | `/knowledge-bases` | login | create/search/sort/view/batch/menu | kb list screenshots |
| 10 | `/knowledge-bases/:id?tab=uploads` | KB exists | upload fixture PDF | upload submitted |
| 11 | `/knowledge-bases/:id?tab=import-status` | import job exists | observe status | completed or honest failure |
| 12 | `/knowledge-bases/:id?tab=papers` | import complete | open paper | read route |
| 13 | `/knowledge-bases/:id?tab=search` | chunks exist | search and open evidence | read highlight |
| 14 | `/read/:id` | paper exists | PDF, page, tabs, notes, highlight | read screenshots |
| 15 | `/chat` | login | generic message streaming | completed answer |
| 16 | `/chat?paperId=...` | paper exists | single-paper RAG with citation | citation jump |
| 17 | `/chat?kbId=...` | KB chunks exist | KB RAG with citation | evidence answer |
| 18 | `/chat?paper_ids=...` | two papers exist | compare-scope follow-up | compare card or honest fallback |
| 19 | `/notes` | login | folder, note, autosave, delete | saved note |
| 20 | `/compare` | two papers exist | compare matrix, save, chat | matrix screenshot |
| 21 | `/analytics` | eval API optional | overview, filters, diff | analytics screenshot |
| 22 | `/settings` | login | sections, language, display, logout | settings screenshots |

## 6.2 浏览器执行模板

每页执行时复制以下模板到测试记录：

```markdown
### <order>. <route>
- start time:
- data ids:
  - kb_id:
  - paper_id:
  - source_chunk_id:
- browser-use commands:
  - `browser-use open ...`
  - `browser-use state`
- expected:
- actual:
- screenshots:
- result: PASS | FAIL | BLOCKED
- notes:
```

## 7. 当前自动化覆盖缺口

按当前仓库状态，最值得优先补的不是通用 UI snapshot，而是以下缺口：

1. Chat query param 与 handoff 恢复矩阵仍可继续加深。
2. Read 的 `source_id` 高亮与 `panel`/`page` URL 恢复缺少明确页面级自动化。
3. Notes 的 URL 恢复、文件夹先行工作流、系统摘要转笔记缺少页面级自动化。
4. KB Detail 的 `runs/review/chat` 深链还可以补更多端到端场景。
5. Settings 各 section 的真实交互覆盖偏浅。
6. Landing 与 auth 页更多依赖手工 walkthrough，自动化阻断度不够。
7. `browser-use` 当前缺少稳定 JSON 执行报告落盘，本 runbook 需要人工填写 `6.2` 模板或转写为 Playwright。
8. Upload worker status、SQL `paper_chunks`、Milvus evidence、Read source highlight 的四段一致性仍需要一条端到端自动化。
9. Chat partial/abstain 的原因归类还缺少自动化断言，需要把 retrieval trace、answer contract 和 UI badge 串起来。

## 8. 最小阻断集

如果要先建立一套“每次前端改动都必须过”的最小阻断集，建议是：

1. `npm run type-check`
2. Chat 相关 Vitest：
   - `ChatWorkspaceV2.test.tsx`
   - `useChatSend.test.tsx`
   - `useChatScopeController.test.ts`
   - `chatHandoff.test.ts`
3. KB 相关 Vitest：
   - `KnowledgeWorkspaceShell.test.tsx`
   - `useKnowledgeBaseWorkspace.test.tsx`
   - `useKnowledgeBaseSearch.test.tsx`
4. Search 相关 Vitest：
   - `Search.test.tsx`
   - `SearchKnowledgeBaseImportModal.test.tsx`
5. Playwright：
   - `chat-critical.spec.ts`
   - `kb-critical.spec.ts`
   - `retrieval-critical.spec.ts`
   - `chat-session-search.spec.ts`
   - `search-pagination-stability.spec.ts`

## 9. 审查结论

这份文档覆盖了当前真实前端的：

1. 全部公开路由
2. 全部受保护路由
3. KB detail 的全部 tabs
4. Read 的全部右侧 tabs
5. Settings 的全部 section
6. Chat 的 query param、scope、handoff、session、streaming、evidence、responsive 深测要求

它可以直接作为：

1. 前端全面浏览器 walkthrough 清单
2. Playwright 扩写基线
3. 手工回归验收 checklist
4. 后续前端测试治理的页面真源

## 10. 执行记录（2026-05-05）

本节只记录已经实际执行并拿到证据的项目，不把 runbook 预期写成已完成。

### 10.1 环境与主链前提

已确认当前主模型链路在线：

1. generation：`glm-4.6v-flashx`
2. embedding：DashScope `text-embedding-v4`
3. rerank：DashScope `qwen3-rerank`

本轮测试沿用的已落地修复基线：

1. phase2 embedding/rerank 主链改为在线 provider
2. Milvus 1024 维自愈
3. `paper_chunks` SQL 持久化补齐
4. landing/介绍页无法进入已修复
5. chat 单论文回答从假性 abstain 恢复为真实回答
6. chat 前端消息同步覆盖问题已修复
7. KB search -> read `sourceChunkId` contract 已修复
8. evidence/source 改为数据库优先，不再仅依赖本地 artifact
9. summary 命中已补 representative chunk 映射，避免把 Milvus auto-id 当成 source id

### 10.2 已完成浏览器 walkthrough

#### PASS-landing-dashboard-auth

已确认：

1. `/` 与介绍页可进入，不再出现“介绍页面无法进入”问题。
2. 登录后可进入 `/dashboard`。
3. Dashboard 仍作为导航/指挥台使用，不承担具体执行。

#### PASS-search-standard-flow

路径：`/search`

已确认：

1. 普通查询 `large language model retrieval` 可返回结果。
2. 结果列表正常渲染。
3. 外部结果卡片 `Import` 可拉起知识库选择弹窗。

当前结论：

1. Search 普通检索主链可用。
2. Search -> Import to KB UI 主链可用。

#### PASS-search-authors-mode-basic

路径：`/search`

已确认：

1. authors 模式下，查询长度小于 3 个字符时不会进入正式作者结果态。
2. 输入 `Hinton` 后能返回作者结果。

观察：

1. 返回名称表现为 `J. Hinton`、`A. Hinton` 等缩写形式。
2. 已确认这是后端/API 数据返回形态，不是前端裁切导致。

当前判断：

1. 属于数据质量/排序表现问题，不是当前主链阻断。
2. 暂未作为本轮 blocker 修复。

#### PASS-notes-page-load-and-render

路径：`/notes`

已确认：

1. Notes 页面可进入。
2. 列表能渲染普通笔记与系统生成摘要。
3. 选中具体 note 后，右侧编辑区可正常显示。
4. 已看到 linked evidence 区域及 `Open source`、`Continue in Chat` 入口。

工具备注：

1. 本页复杂卡片在 `browser-use click` 下不稳定。
2. 通过 DOM 触发 `target.click()` 能稳定选中 note。
3. 因此本页不能仅凭 CLI click 抖动就判产品失败。

#### PASS-notes-open-source-and-chat-handoff

路径：`/notes`

已确认：

1. 选中 evidence note 后，右侧 `Linked Evidence` 区显示 `Open source` 与 `Continue in Chat`。
2. `Open source` 触发后，目标 URL 为：
   - `/read/e83c8887-04f8-422f-94d6-bbd304283aa5?page=1&source=evidence&source_id=chunk_7e9a7e7ef7ac5b33624e5679`
3. 该 URL 已使用稳定业务 `chunk_*` id，不再是旧数值型 source id。
4. 直接打开该 Reader URL 后，右侧出现：
   - `source highlight: chunk_7e9a7e7ef7ac5b33624e5679`
   - `Evidence Side Note`
5. `Continue in Chat` 触发后，URL 进入：
   - `/chat?paperId=e83c8887-04f8-422f-94d6-bbd304283aa5&handoff=1&new=1`
6. Chat 页面显示 Compare/Notes 来源 handoff 状态与预填继续提问提示。

当前结论：

1. Notes -> Read -> source highlight 主链已恢复。
2. Notes -> Chat handoff 主链已恢复。

#### PASS-settings-page-basic

路径：`/settings`

已确认：

1. 页面可进入。
2. 页面显示 `个人资料`、`语言设置`、`显示设置`、`安全设置`、`API 集成`、`系统诊断` 等 section。
3. 右侧状态区可见 `系统诊断`、`存储使用量`、`系统流`。

备注：

1. 本轮主要完成页面级 smoke 与 section 存在性确认。
2. 细粒度交互如登出、每个 section 的编辑行为仍可继续深测。

#### PASS-analytics-page-basic

路径：`/analytics`

已确认：

1. 页面可进入。
2. 页面显示 `评测看板`。
3. 页面展示最近离线门禁、运行详情、查询族分布等内容区。
4. 当前数据态不是空白页，也不是错误页。

#### PASS-compare-workspace-mainline

路径：`/compare`

已确认：

1. 页面可进入。
2. 使用 `LIMA` 检索后可选中两篇论文。
3. 选中两篇论文后，`生成对比表` 按钮解锁。
4. 点击后成功生成 compare matrix，并出现 `跨论文洞察` 区域。
5. 顶部 `保存到笔记` 可成功执行，并出现成功提示：
   - `对比结果已保存到笔记`
6. 顶部 `带入 Chat 继续问` 可进入：
   - `/chat?paper_ids=e83c8887-04f8-422f-94d6-bbd304283aa5,0bac4a46-46b2-4712-9422-3cc8bf1b5070&handoff=1`
7. 进入 Chat 后显示：
   - `来自 Compare`
   - `已为你预填下一条问题，确认后再发送。`

当前结论：

1. Compare 主工作流已跑通。
2. Compare -> Notes 与 Compare -> Chat 两条 handoff 已跑通。

### 10.3 本轮发现并已修复的问题

#### FIXED-notes-legacy-evidence-source-id

问题现象：

1. Notes 中旧 evidence note 持久化了数值型 `source_chunk_id`。
2. `Open source` 会生成 `/read/...source_id=466045819771397202` 之类的旧数值 id。
3. 这会破坏 Read 页稳定跳转与高亮契约。

根因判断：

1. 问题不在前端按钮本身，而在后端 notes contract 信任了历史脏数据。
2. 旧数据里存的是内部/Milvus 风格 id，而不是稳定业务 `chunk_*` id。
3. 仅靠本地 artifact 修补不可靠，因为当前环境 `load_chunk_index()` 返回为空。

已实施修复：

1. Notes 响应格式化改为 DB-first canonicalization。
2. 保存 evidence note 时同步 canonicalize，避免继续写入数值型 source id。
3. artifact resolver 仅保留为 fallback，而非唯一真源。

涉及文件：

1. `apps/api/app/services/evidence_contract_service.py`
2. `apps/api/app/api/notes.py`
3. `apps/api/tests/unit/test_notes_contract_helpers.py`
4. `apps/api/tests/unit/test_notes_evidence_canonicalization.py`

真实验证：

1. 对实际 legacy note 进行异步格式化后，`source_chunk_id` 已变为稳定 `chunk_*`。
2. `citation_jump_url` 已对应 canonical `source_id=chunk_7e9a7e7ef7ac5b33624e5679`。

### 10.4 已完成窄验证

#### PASS-backend-notes-canonicalization-tests

执行命令：

```bash
cd apps/api && PYTHONPATH=$(pwd) .venv/bin/pytest -q tests/unit/test_notes_contract_helpers.py tests/unit/test_notes_evidence_canonicalization.py
```

结果：

1. `7 passed`

#### PASS-frontend-type-check

执行命令：

```bash
cd apps/web && npm run type-check
```

结果：

1. 通过

#### PASS-reader-evidence-highlight-regression-check

验证方式：

1. 直接打开 canonical Reader URL：
   - `/read/e83c8887-04f8-422f-94d6-bbd304283aa5?page=1&source=evidence&source_id=chunk_7e9a7e7ef7ac5b33624e5679`

结果：

1. Reader 页面成功进入。
2. 右侧显示 `Evidence Side Note`。
3. `source highlight` 与 `chunk_7e9a7e7ef7ac5b33624e5679` 对齐。

### 10.4.1 本轮新增验证（2026-05-05 持续）

#### PASS-auth-live-login-after-backend-recovery

路径：`/login` -> `/dashboard`

已确认：

1. 在后端恢复可用后，固定账号 `pr19-e2e@example.com` / `Pr19E2EPass123` 可真实登录成功。
2. 登录提交后 URL 到达 `/dashboard`。
3. Dashboard 主内容、左侧导航、最近对话与知识库区块均已渲染。
4. 本轮之前对 `dev proxy upstream unavailable` 的根因修复在真实后端恢复后未引入登录回归。

补充观察：

1. 登录页首屏未登录访问 `/api/v1/auth/me` 返回 `401` 属预期冷启动行为。
2. 在后端健康状态正常时，不再出现此前的代理 `500` 误报。

#### PASS-chat-main-entry-after-backend-recovery

路径：`/chat`

已确认：

1. Chat 页面可进入。
2. 页面显示 scope 状态、推荐 prompt、composer 与右侧状态区。
3. 会话与知识库上下文能从 API 拉取并进入页面状态。
4. 未出现白屏或阻断式异常。

补充观察：

1. 控制台中观察到部分请求存在重复调用信号，需要后续再做性能/幂等性深测。
2. 当前未判定为主链阻断。

#### FIXED-notes-preferences-update-loop

问题现象：

1. `/notes` 页面在真实浏览器手测中触发 `Maximum update depth exceeded`。
2. 报错稳定指向 `NotesContent`，并导致页面持续重复渲染。

根因判断：

1. `Notes` 页面存在多个根据 query/filter/folder 互相校正的 `useEffect`。
2. `notesPreferencesStore` 中 `setSelectedFolderId` / `setTagFilter` 每次调用都无条件写入状态。
3. 即使值未变化，也会触发 Zustand 持久化状态更新，放大为 effect -> setter -> rerender -> effect 的循环。
4. 这属于状态层幂等性缺失，而不是单个 effect 条件判断的小补丁问题。

已实施修复：

1. 在 `apps/web/src/features/notes/state/notesPreferencesStore.ts` 中，将 `setSelectedFolderId` 与 `setTagFilter` 改为幂等 setter。
2. 当目标值与当前值相同，直接返回原状态，不再触发无意义更新。
3. 修复保持原有 UI 与工作流不变，只从状态边界消除循环根因。

验证结果：

1. `cd apps/web && npm run type-check` 通过。
2. 后续需继续在同一登录会话下补做 `/notes` 浏览器复验，确认控制台不再出现 update depth 报错。

#### FIXED-auth-form-autocomplete-accessibility

问题现象：

1. 浏览器控制台在登录页持续提示输入框缺少 `autocomplete` 属性。
2. 这不是视觉问题，但属于已被浏览器明确报告的表单可访问性缺口。

已实施修复：

1. `apps/web/src/app/pages/Login.tsx`
   - 邮箱字段补 `autoComplete="email"`
   - 密码字段按模式补 `current-password` / `new-password`
2. `apps/web/src/app/pages/Register.tsx`
   - 姓名补 `autoComplete="name"`
   - 邮箱补 `autoComplete="email"`
   - 密码与确认密码补 `autoComplete="new-password"`

约束说明：

1. 仅补表单语义属性。
2. 未改动整体视觉风格、版式或交互结构。

验证结果：

1. 两次 `cd apps/web && npm run type-check` 均通过。
2. 后续需在浏览器中再次确认控制台 issue 是否消失。

#### PASS-settings-slice-remediation-and-tests

路径：`/settings`

已确认：

1. `显示设置` 已改为随当前语言显示正确中文副文案：`自定义阅读与界面尺寸`。
2. `安全设置` 已从占位输入框改为真实密码修改表单，并接入 `usersApi.changePassword`。
3. `API 集成` 已改为本地化文案、内联错误态和对话框式删除确认，不再使用浏览器 `prompt()`。
4. `系统诊断` 已改为沿用当前主题的卡片样式，并补充空态/错误态显示。
5. 设置页相关单测与新增错误归一化测试均已通过。

执行命令：

```bash
cd apps/web && npm run test:run -- src/app/pages/Settings.test.tsx src/app/components/APIKeyManager.test.tsx src/utils/resolveApiErrorMessage.test.ts
cd apps/web && npm run type-check
```

结果：

1. 相关测试共 `6 passed`。
2. `type-check` 通过。

补充说明：

1. 已在浏览器中确认 `显示设置` 中文文案生效。
2. 后续对 `安全设置` 实际改密、`API 集成` 真后端成功流和 `系统诊断` 在线数据流的复验，被当前 backend 启动阻塞，不能提前记为完成。

#### PASS-auth-pages-copy-semantics-refresh

路径：`/register`、`/forgot-password`、`/reset-password`

已确认：

1. `Forgot Password` 邮箱输入已补 `autocomplete="email"` 与 `inputMode="email"`。
2. `Reset Password` 两个密码输入已补 `autocomplete="new-password"`，中文占位文案统一为 `至少 8 个字符`。
3. `Register` 权益区已从 emoji 列表改为设计系统内图标卡片，保持当前暖色纸面风格。
4. 三页错误处理已统一接入本地化 API 错误归一化 helper，避免 `Network Error` / `Request failed ...` 原样漏到页面或 toast。

执行命令：

```bash
cd apps/web && npm run test:run -- src/app/pages/AuthPages.test.tsx src/app/pages/Settings.test.tsx src/app/components/APIKeyManager.test.tsx src/utils/resolveApiErrorMessage.test.ts
cd apps/web && npm run type-check
```

浏览器证据：

1. `/forgot-password` 实测读取到 `autocomplete=email`、`inputmode=email`。
2. `/reset-password?token=demo-token` 实测读取到两个密码框均为 `autocomplete=new-password`。
3. `/register` 左侧 `账户权益` 区已不再出现 emoji 字符，而是图标卡片。

结果：

1. 相关测试总计 `9 passed`。
2. `type-check` 通过。

#### BLOCKED-backend-compose-stale-image

阻断现象：

1. 当前 `docker compose up -d --pull never postgres redis neo4j etcd minio milvus-standalone backend` 可拉起数据库与向量链路。
2. `backend` 容器停在 `Created` / `Starting`，最终报错：`exec: "uvicorn": executable file not found in $PATH`。

根因定位：

1. 当前 compose 使用的是本地旧镜像 `scholar-ai-backend:latest`。
2. 该镜像创建时间为 `2026-04-13`，镜像默认 `Cmd` 是 `uvicorn app.main:app ... --reload`。
3. 直接检查镜像环境后，镜像内不存在 `uvicorn` 可执行文件，说明不是当前前端改动引入，而是测试环境中的陈旧 backend 镜像问题。

影响范围：

1. 已登录页的真实 API 成功流复验目前被阻断。
2. 前端在 Vite dev server 下仍可继续验证公开页面与离线/异常态，但不能把依赖真实 backend 的浏览器主链提前记为 PASS。

### 10.5 当前未完成项

以下项目仍需继续浏览器复验，不应提前记为完成：

1. `/settings` 页面与登录态恢复、登出、模型展示一致性深测
2. `/analytics` 页面筛选、明细切换等交互深测
3. `/settings` 页面在 backend 恢复后的改密成功流、API key 成功流、诊断数据流浏览器复验
4. Chat 页面继续做更完整的多来源 handoff、发送、返回、scope 切换复验

### 10.6 当前结论

截至 2026-05-05 本轮记录时：

1. Search、Dashboard、Landing、Notes 基础进入与主链已具备实际通过证据。
2. Notes 的 legacy evidence source id 已完成根因修复，并已用后端窄测试证明 contract 生效。
3. 当前剩余工作主要是继续把浏览器 walkthrough 跑完，并将每个页面的 PASS/FAIL/BLOCKED 写回本 runbook。

## 10.7 执行记录（2026-05-06）

#### PASS-auth-route-guard-and-live-login

路径：`/login`、`/dashboard`、受保护路由 `/compare`

已确认：

1. 未登录直接打开受保护路由 `/compare?...` 会回到 `/login`。
2. 使用固定账号 `pr19-e2e@example.com / Pr19E2EPass123` 可再次真实登录成功。
3. 登录后可进入 `/dashboard`，工作区主导航、最近对话、资料馆藏均正常渲染。

执行方式：

1. 使用 `browser-use` 备用链路在独立 session 中打开 `/login` 和 `/compare?...`。
2. 使用固定账号完成真实登录后复验路由回跳与 dashboard 进入。

结果：

1. 认证主链正常。
2. 受保护路由守卫正常。

#### FIXED-login-page-version-copy-drift

路径：`/login`

问题现象：

1. 登录页左上角仍显示 `个人研究资料库`、`v1.0`，右上角仍显示 `测试版`。
2. 该文案与当前 v4.0 顶层状态、当前在线模型链路不一致。

已实施修复：

1. `apps/web/src/app/pages/Login.tsx`
2. 左侧副标题改为 `个人研究工作台`
3. 版本标记改为 `v4.0`
4. 移除右上角 `测试版 / Beta Version` 角标

验证结果：

1. `cd apps/web && npm run type-check` 通过。
2. 浏览器重新打开 `/login` 后，顶部文案已更新为 `v4.0`。

#### FIXED-notes-placeholder-title-and-summary-preview

路径：`/notes`

问题现象：

1. 历史论文标题占位值 `Paper <id>` / `未命名论文` 会直接泄露到系统摘要与笔记列表。
2. 摘要预览会暴露 `1. Research Question & Motivation`、`Problem Addressed`、半截 markdown 等内部草稿结构。

根因定位：

1. 后端 `sanitize_paper_display_metadata()` 旧逻辑仍会把坏标题降级成 `Paper <id>`。
2. 前端把 `未命名论文` 当作真实标题处理，导致不再从 `readingNotes` 中派生可读标题。
3. 摘要预览先截断再清洗，历史脏摘要中的半截 heading / markdown 无法被正确归一化。

已实施修复：

1. `apps/api/app/services/paper_display_metadata.py`
   - 坏标题无作者时不再返回 `Paper <id>`，统一降级为 `未命名论文`
2. `apps/api/tests/unit/test_paper_display_metadata.py`
   - 补作者 fallback 与坏标题回归测试
3. `apps/web/src/features/notes/content.ts`
   - 将 `未命名论文`、`系统摘要` 纳入占位标题集合
   - 新增摘要标题/预览推导与历史半截 heading / markdown 清洗规则
4. `apps/web/src/app/pages/Notes.tsx`
   - 系统摘要卡片改为直接基于原始 `readingNotes` 推导预览，不再先错误截断
5. `apps/web/src/features/notes/content.test.ts`
   - 新增 notes 内容归一化回归测试

执行命令：

```bash
cd apps/api && PYTHONPATH=$(pwd) .venv/bin/pytest -q tests/unit/test_paper_display_metadata.py
cd apps/web && npm run test:run -- src/features/notes/content.test.ts src/features/notes/ownership.test.ts
cd apps/web && npm run type-check
```

结果：

1. `notes` 相关前端测试 `9 passed`
2. 后端标题清洗测试通过
3. 浏览器复验确认：
   - `Paper 142c2950` 已不再出现在主链列表中
   - 多数系统摘要卡片已显示真实可读标题与正文式预览

剩余观察：

1. 仍有少量历史摘要数据本身只有截断内容，例如 `Problem Address`、`摘要`，这属于旧数据质量残留，不再是当前显示链主因。

#### FIXED-compare-dimension-selection-hardening-partial

路径：`/compare`、`POST /api/v1/compare/v4`

问题现象：

1. compare 页面可以正常生成矩阵，但真实内容仍把弱相关句子塞进维度单元格。
2. 典型错误包括：
   - `研究问题`: `6 out of 10 prompts with malicious intent).`
   - `方法`: `this small sample adds diversity...`
   - `数据集`: `Ablation experiments reveal vastly`
   - `指标`: `what is striking about this result...`

根因定位：

1. 后端 compare 主链虽然已支持多 query 与维度打标，但 `_fill_cell()` 仍允许仅凭 `section=introduction` 之类的弱 hint 入选。
2. 维度语义不足的句子会被 section bonus 抬进结果单元格。

已实施修复：

1. `apps/api/app/services/compare_service.py`
   - 强化 snippet 级维度语义判定
   - 对 `problem/method/dataset/metrics/limitations/innovation` 启用严格语义门槛
   - 若片段缺少该维度正向语义词，则不再允许只靠 section hint 入选
2. `apps/api/tests/unit/test_phase4_hybrid_compare.py`
   - 新增 problem/metrics 弱语义拒绝测试
   - 现有 compare 回归共 `24 passed`

执行命令：

```bash
cd apps/api && PYTHONPATH=$(pwd) .venv/bin/pytest -q tests/unit/test_phase4_hybrid_compare.py
```

结果：

1. compare 单测 `24 passed`
2. 真实 API 复验显示：
   - `problem` 现已退回 `not_enough_evidence`
   - `dataset` 现已退回 `not_enough_evidence`
   - `metrics` 现已退回 `not_enough_evidence`

当前剩余缺口：

1. `method` 仍可能选到泛化训练描述句，如 `this small sample adds diversity...`
2. `results` 仍可能选到偏 commentary 的句子，如 `what is striking about this result...`
3. compare 主链已从“明显错误表格”收敛到“过于保守且局部仍有弱证据”，但还不能记为完全通过。

#### 当前阶段结论（截至 2026-05-06）

1. 登录/受保护路由、dashboard 进入、在线模型展示主链已正常。
2. notes 主链已从“占位标题 + 草稿泄露”修到“基本可用，仅剩少量历史脏数据残留”。
3. compare 页面功能主链正常，但内容质量仍未完全达标，后续应继续收紧 `method` / `results` 维度证据选择。
