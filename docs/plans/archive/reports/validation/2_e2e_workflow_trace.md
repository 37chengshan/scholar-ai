# E2E Workflow Trace Analysis

## 1. 最小核心流程链路追踪

### 阶段一：Auth (登录与鉴权)
1. **Frontend**: 用户在 `Login.tsx`（杂志风格/终端风组件）点击登录。调用 `useAuth()` hook。
2. **Client API**: `useAuth` 调用 `authApi.login()`。由于配置了 `withCredentials: true`，不依赖 localStorage 传递令牌。
3. **Backend API**: `POST /api/v1/auth/login` （`auth.py`）。
4. **Service**: 调用 `authenticate_user`，生成基于 HttpOnly 的 Access + Refresh Cookies 下发给前端。
5. **后续调用**: 通过 Axios Interceptor，所有请求自动附带 Cookie 并能在过期时实现无感刷新 (`/api/v1/auth/refresh`)。
*   **打通情况：完全打通并已落地。**

### 阶段二：创建知识库 (KB Creation)
1. **Frontend**: `KnowledgeBaseList.tsx` 中的 `CreateKnowledgeBaseDialog` 组件触发操作。
2. **Client API**: `kbApi.create(data)` 发起调用。
3. **Backend API**: `POST /api/v1/kb/`，携带 `KnowledgeBaseCreateDto` 载荷。
4. **Persistence**: 写入数据库，生成唯一 `UUID`。
*   **打通情况：完全打通。状态维护通过 `useKnowledgeBases` Hook 下拉刷新。**

### 阶段三：上传论文 (Paper Upload)
1. **Frontend**: 在 `KnowledgeBaseDetail` 页面，点击上传调用 `useUpload.ts` Hook。
2. **Client API Workflow**:
    *   第一步：验证后，`uploadApi.getUploadUrl()` 获取预签名 URL 和 `paperId` (`POST /api/v1/papers/`)。
    *   第二步：如果处于云端模式，直传 S3 / 如果本地开发，调用 `POST /api/v1/papers/upload/local/{key}`。
    *   第三步：使用 `uploadApi.confirmUpload()` 完成上传状态确认 (`POST /api/v1/papers/webhook`)。
3. **Backend API**:
    *   进入 `paper_upload.py`，触发 Webhook，此时会调用后台 Celery/Task (`ProcessingTask`) 进行 PDF 解析和 Embedding。
*   **打通情况：完全打通。这是核心的数据流水线入口。**

### 阶段四：Chat / RAG 问答与工具调用
1. **Frontend**: `ChatWorkspace.tsx` 与底层的 `ChatLegacy.tsx`，通过 `useChatStream.ts` 管理流。
2. **SSE Connection**: UI 绑定 `message_id` 初始化 `EventSource` 请求 `POST /api/v1/chat/stream`，此时前端实现了 100ms throttle 以及严格的状态机 guard。
3. **Backend RAG**: 
    *   `chat.py` 流式控制器启动。
    *   底层通过 `AgenticRetrievalOrchestrator` (`app.core.agentic_retrieval`) 工作。
    *   第一步：`routing_decision` 判断使用哪些数据（Task 1.4）。
    *   第二步：触发 `thought` 事件。
    *   第三步：如果需要搜索文档，触发并发子查询（Multimodal Search/Milvus）。
    *   第四步：如果触发外部工具（如 Scholar API搜索等），下发 `tool_call` 与 `tool_result` 并在 UI 层 `ChatLegacy.tsx` 渲染面板。
    *   第五步：LLM 吐出 `message` chunks。
    *   最终发回 `done`。
*   **打通情况：全链路打通。** 前端甚至对 `thought` (思维树) 提供独立 Buffer，这符合 DeepSeek 深度思考模型或多智能体推理交互范式设计。

## 2. 结论判定
**当前项目最小核心流程 (Auth -> KB -> Upload -> RAG/Chat) 链路清晰、代码路径齐备，逻辑处于完全闭环可用状态。**