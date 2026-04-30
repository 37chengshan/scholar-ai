# API Alignment & Layering Analysis

## 1. 现状概述 (Executive Summary)
本项目已在 `feat/pr6-contracts-kb-chat` 分支阶段进行了一次关键的“契约收口”重构，目的是收敛前后端 API 契约，建立 `packages/types` 和 `packages/sdk` 的共享包（monorepo 模式）来强对齐接口。

## 2. API 接口对齐 (API Contract Alignment)

### 2.1 共享契约与 SDK
项目采用了极佳的工程实践，通过独立的共享层来实现接口对齐：
*   **`packages/types`**: 存放了全域的 DTO 定义，如 `KnowledgeBaseDto`, `MessageDto`, `SessionDto`, 以及基础错误和分页类型。
*   **`packages/sdk`**: 提供了一个定制化的 `HttpClient`，封装 Axios 与 DTO 绑定，同时导出了针对 `chat, kb, papers` 模块强类型绑定的 API clients。

### 2.2 设计规范 (API Design Code Review)
*   **RESTful 标准**: 后端 API 路由设计清晰，且资源路径合规（如 `GET /api/v1/kb`, `POST /api/v1/chat/stream`）。
*   **HTTP Methods & Response**: 后端（FastAPI）严格遵守了 Pydantic Schema 的返回，前端去处了原有的强转逻辑，强制依赖 SDK 的接口返回值。
*   **错误处理 (RFC 7807)**: API 使用了 `setup_error_handlers` 中定义的统一问题详细信息响应结构。前端 `apiClient` 能将鉴权失败识别为 `AuthError`，拦截器处理超时和刷新 Token，非常规范。
*   **别名处理 (Alias handling)**: 后端 Pydantic 模型（如 KB 和 Chat 相关的 Schema）直接使用了标准的 snake_case 并且未见强制开启 camelCase generator。前端在 SDK 中直接与该 DTO 层适配。

## 3. 前后端分层落地分析

### 3.1 前端分层结构 (Frontend Layering)
*   **UI Components**: `apps/web/src/app/pages` 和 `features/`。
*   **State Management/Hooks**: `hooks/` / `features/*/hooks/`
*   **API Client Layer**: 原有的 `services/*Api.ts` 已经开始过渡包裹 `@scholar-ai/sdk` (`sdkHttpClient`)。
*   **对齐程度**: 很好地隔离了视图与数据。`check-code-boundaries.sh` 脚本强制验证视图层不能直接使用 Axios/fetch，这确保了关注点分离。

### 3.2 后端分层结构 (Backend Layering)
*   **Router (Controller)**: `app.api` 承接 HTTP 请求校验并解包。
*   **Service (Business Logic)**: `app.services` 与 `app.core` 分离业务。如 `auth_service.py` 处理用户态鉴权，`agentic_retrieval.py` 和 `multimodal_search_service.py` 处理核心 AI 链路。
*   **Data Access (Repository)**: 独立于 API，如 `paper_crud.py` 内部解除了复杂的查询杂糅，交给底层处理。

## 4. 漏洞与改进空间
1.  **DTO 命名潜藏转换风险**: TS 侧使用 camelCase (`paperCount`)，Python 侧若不显式处理 alias，直接使用 `paper_count` 时，中间会引发解析不到字段的问题。在 `pr6` 阶段，通过在 fetch 层或 Pydantic 中使用 `alias_generator` 是必要的，目前 `packages/types` 已写为 camelCase (`paperCount`) 而 Python schema 未明确开启 camelCase 配置。这是一个潜在接口错位雷区，需要依赖拦截器。
2.  **SDK 承接的不完整性**: 仍然保留了大量 `.ts` 直连 (`uploadApi.ts`, `authApi.ts`) 未迁移到 `@scholar-ai/sdk`，架构迁移处于中间态（Bridge phase）。

## 5. 结论
分层落地**优秀**，具有严格的企业级规范；契约对齐**方向正确但需注意字段命名风格桥接** (camelCase vs snake_case)。总体可用度极高，是一套扎实的工程。