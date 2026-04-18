# API Contract

## Purpose

统一 ScholarAI API 的路由、响应、错误、分页、鉴权、命名与 SSE 约定，避免接口形态漂移。

## Scope

适用于新的 HTTP/SSE 接口，以及对现有接口的重构与兼容迁移。

## Source of Truth

- 仓库级契约：docs/architecture/api-contract.md
- 后端实现细节：apps/api/docs/API_CONTRACT.md
- 资源生命周期：docs/domain/resources.md
- 跨端共享契约：packages/types
- 跨端 typed client：packages/sdk

## Rules

路由前缀规范：

- 统一使用 /api/v1 作为版本前缀。
- 同一资源只允许一套路由命名，不允许并存平行命名。

成功响应格式：

```json
{
  "success": true,
  "data": {},
  "meta": null
}
```

列表响应格式：

```json
{
  "success": true,
  "data": {
    "items": []
  },
  "meta": {
    "limit": 20,
    "offset": 0,
    "total": 100
  }
}
```

分页资源样板（papers）：

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "paper-uuid",
        "title": "Attention Is All You Need",
        "authors": ["Ashish Vaswani"],
        "status": "completed",
        "arxivId": "1706.03762",
        "createdAt": "2026-04-16T08:00:00Z",
        "updatedAt": "2026-04-16T08:05:00Z"
      }
    ]
  },
  "meta": {
    "limit": 20,
    "offset": 0,
    "total": 1
  }
}
```

错误响应格式（RFC 7807）：

```json
{
  "type": "https://scholarai/errors/validation",
  "title": "Validation Error",
  "status": 400,
  "detail": "Field title is required",
  "instance": "/api/v1/papers"
}
```

分页规范：

- 请求参数：limit、offset
- 响应字段：meta.limit、meta.offset、meta.total
- 兼容期可接受 page+limit 输入，但后端内部统一归一化到 limit+offset。

鉴权规范：

- 受保护路由必须显式声明鉴权依赖。
- 未认证返回 401，已认证但无权限返回 403。
- 不在响应中泄露密钥、令牌或内部鉴权策略细节。

字段命名规则：

- 后端内部（ORM/DTO/schema）：snake_case
- 前端模型（props/store/view-model）：camelCase
- 命名风格转换只在 API 边界进行一次。

SSE 事件规范：

- 事件类型：thought、tool_call、tool_result、confirmation_required、message、error、done
- 每个事件必须包含可解析 JSON 载荷。
- 长连接必须有 heartbeat 或等价保活策略。
- done 为唯一完成事件，不得与错误事件混用。
- Chat 流式接口仅接受 canonical 事件类型，不再支持 legacy alias 映射。
- 除 heartbeat 外，所有业务事件必须携带 `message_id`。

Import Pipeline 契约补充：

- 创建导入任务：`POST /api/v1/knowledge-bases/{kb_id}/imports`
- 单文件上传：`PUT /api/v1/import-jobs/{job_id}/file`
- 批量创建导入任务：`POST /api/v1/knowledge-bases/{kb_id}/imports/batch`
- 批量本地文件上传：`POST /api/v1/import-batches/{batch_id}/files`
- dedupe 决策：`POST /api/v1/import-jobs/{job_id}/dedupe-decision`

批量本地文件上传响应要求：

- `data.accepted[]` 返回已入队条目
- `data.rejected[]` 返回拒绝条目与 `reason`
- 允许部分成功，不允许静默丢弃

Chat 流协议真源：

- app/models/chat.py 为 Chat SSE 事件 DTO 与 envelope 真源。
- app/services/chat_orchestrator.py 负责 message_id 绑定与事件编排。
- app/api/chat.py 负责 stream 接口对外契约。

Chat stream 请求体契约（冻结）：

- 路径：`POST /api/v1/chat/stream`
- 请求体：

```json
{
  "session_id": "session-uuid",
  "message": "请总结这篇论文的贡献",
  "mode": "auto",
  "scope": {
    "type": "paper",
    "paper_id": "paper-uuid"
  },
  "context": {
    "auto_confirm": false
  }
}
```

- 字段语义：
  - `mode`：`auto | rag | agent`，默认 `auto`。
  - `scope.type`：`paper | knowledge_base | general`。
  - `scope.paper_id` 仅在 `scope.type=paper` 时有效。
  - `scope.knowledge_base_id` 仅在 `scope.type=knowledge_base` 时有效。
  - `context`：可选扩展上下文，保持向后兼容。

Session messages 契约（冻结）：

- 路径：`GET /api/v1/sessions/{session_id}/messages`
- 查询参数：`limit`、`offset`、`order(asc|desc)`
- 响应体：

```json
{
  "success": true,
  "data": {
    "session_id": "session-uuid",
    "messages": [],
    "total": 120,
    "limit": 50,
    "offset": 0,
    "order": "desc",
    "pagination": {
      "has_more": true,
      "returned": 50,
      "next_offset": 50
    }
  }
}
```

- 分页语义：
  - `total` 是该会话消息全量总数，不是当前页长度。
  - `returned` 是本次返回条数。
  - `next_offset` 基于 `offset + returned` 计算。

Paper 资源契约补充：

- `GET /api/v1/papers`：返回 `data.items[]` 与 `meta.limit/offset/total`。
- `GET /api/v1/papers/{paperId}`：返回单资源结构，字段命名遵循边界转换规则。
- `POST /api/v1/papers/{paperId}/star`：只允许返回统一 envelope，不允许裸布尔返回。
- `POST /api/v1/papers/batch-delete`：批量删除必须返回可追踪结果（成功列表与失败列表）。

Plan C 契约治理约束：

- 契约表面改动（apps/api/app/api, apps/api/app/models, apps/web/src/services, packages/types, packages/sdk）必须同步更新本文件与 `docs/domain/resources.md`。
- 任何 fallback 契约兼容必须在 `docs/governance/fallback-register.yaml` 登记到期时间与删除计划。

## Required Updates

- 新增接口：同步校验是否符合本契约。
- 改动响应格式：同步更新本文件与调用方。
- 改动 SSE 事件：同步更新 docs/architecture/system-overview.md。

上传会话（PR19）接口补充：

- `POST /api/v1/import-jobs/{jobId}/upload-sessions`
  - 用途：创建或恢复本地 PDF 的分片上传会话，支持秒传命中。
  - 请求：`filename`、`sizeBytes`、`chunkSize`、`sha256`、`mimeType`
  - 响应：`instantImport` 或 `session`（含 `uploadSessionId`、`missingParts`、`progress`）
- `GET /api/v1/upload-sessions/{sessionId}`
  - 用途：拉取会话状态与缺失分片列表，用于断点恢复。
- `PUT /api/v1/upload-sessions/{sessionId}/parts/{partNumber}`
  - 用途：上传单个分片（`application/octet-stream`）。
- `POST /api/v1/upload-sessions/{sessionId}/complete`
  - 用途：合并分片、写入文件元数据并触发 ImportJob 入队。
- `POST /api/v1/upload-sessions/{sessionId}/abort`
  - 用途：终止会话，阻止后续分片写入。

ImportJob `nextAction` 补充：

- 本地文件场景从 `upload_file` 切换为 `create_upload_session`。
- `createSessionUrl` 指向 `/api/v1/import-jobs/{id}/upload-sessions`。

## Verification

- 抽样检查新接口响应是否包含 success/data/meta。
- 抽样检查错误路径是否为 RFC 7807。
- 抽样检查分页接口参数与 meta 字段是否一致。
- 抽样检查受保护接口的 401/403 行为。
- 运行 `cd apps/api && .venv/bin/python -m pytest -q tests/integration/test_imports_chat_contract.py --maxfail=1`，冻结导入批次与 Chat 主链路契约。

## Open Questions

- 是否需要统一错误 type 枚举并下沉到共享 SDK。
- 是否将分页从 offset 模式逐步升级到 cursor 模式。
