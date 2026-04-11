# ScholarAI API 契约文档

## 概述

本文档定义了 ScholarAI 后端 API 的契约规范。前端开发应使用以下来源：

- **OpenAPI 文档**: `/docs` (Swagger UI) 或 `/redoc` (ReDoc)
- **导出文件**: `docs/api/openapi.json` / `openapi.yaml`
- **本契约文档**: 定义核心规范和约定

## API 版本

所有 API 路径统一使用 `/api/v1` 前缀：

```
/api/v1/auth/*
/api/v1/sessions/*
/api/v1/chat/*
/api/v1/papers/*
/api/v1/queries/*
```

## 认证

### 方式 1: Cookie-based (推荐用于 Web 前端)

- **Cookie 名称**: `accessToken` (httpOnly)
- **过期时间**: 1 小时
- **刷新**: `POST /api/v1/auth/refresh` 使用 `refreshToken` cookie

### 方式 2: Authorization Header (用于 API 客户端)

```
Authorization: Bearer <jwt_token>
```

## 通用响应格式

### 成功响应

```json
{
  "success": true,
  "data": { ... }
}
```

### 错误响应 (RFC 7807 ProblemDetail)

```json
{
  "type": "https://scholarai.ai/errors/validation",
  "title": "Validation Error",
  "status": 400,
  "detail": "Field 'title' is required",
  "instance": "/api/v1/papers"
}
```

## SSE (Server-Sent Events) 规范

### 聊天流接口

**端点**: `POST /api/v1/chat/stream`

**请求格式**:

```json
{
  "message": "string",
  "session_id": "uuid | null",
  "context": {
    "auto_confirm": false
  }
}
```

**响应格式**: `text/event-stream`

**事件类型**:

| 事件类型 | 描述 | 数据格式 |
|---------|------|---------|
| `thought` | Agent 思考过程 | `{ type: "thinking", content: "..." }` |
| `tool_call` | 工具调用开始 | `{ type: "tool_call", tool: "...", parameters: {} }` |
| `tool_result` | 工具执行结果 | `{ type: "tool_result", tool: "...", success: bool, data: {} }` |
| `confirmation_required` | 需用户确认 | `{ type: "confirmation_required", confirmation_id: "uuid", ... }` |
| `message` | 最终回复 | `{ type: "message", content: "..." }` |
| `error` | 错误发生 | `{ type: "error", error: "...", details: {} }` |
| `done` | 流结束 | `{ type: "done", tokens_used: int, cost: float }` |

**心跳**: 每 15 秒发送空注释 `:heartbeat`

**重连**: 使用 `Last-Event-ID` header 恢复中断的流

## 分页规范

所有列表接口使用相同的分页参数：

```json
{
  "limit": 20,    // 最大返回数量
  "offset": 0,    // 偏移量
  "total": 100    // 总数量（响应中）
}
```

## 日期时间格式

所有时间字段使用 ISO 8601 格式：

```json
{
  "created_at": "2024-01-15T10:30:00",
  "updated_at": "2024-01-15T11:45:00"
}
```

## 字段命名约定

### 后端 → 前端转换

后端使用 snake_case，前端使用 camelCase。转换在 API 层自动完成：

| 后端字段 | 前端字段 |
|---------|---------|
| `user_id` | `userId` |
| `created_at` | `createdAt` |
| `message_count` | `messageCount` |

## 错误码定义

| HTTP 状态码 | 错误类型 | 说明 |
|-----------|---------|------|
| 400 | `validation` | 参数验证失败 |
| 401 | `unauthorized` | 未认证或 token 无效 |
| 403 | `forbidden` | 无权限访问资源 |
| 404 | `not_found` | 资源不存在 |
| 409 | `conflict` | 资源冲突（如重复创建） |
| 429 | `rate_limit` | 请求频率超限 |
| 500 | `internal` | 服务器内部错误 |

## 健康检查

### Liveness Probe

**端点**: `GET /health/live`

**用途**: Kubernetes 存活检查

**响应**:

```json
{
  "status": "alive",
  "service": "scholarai-ai"
}
```

### Readiness Probe

**端点**: `GET /health/ready`

**用途**: Kubernetes 就绪检查

**响应**:

```json
{
  "status": "ready",
  "service": "scholarai-ai",
  "ai_services": {
    "milvus": { "status": "ready" },
    "reranker": { "status": "not_ready", "note": "Will be initialized on first use" },
    "embedding": { "status": "not_ready" }
  }
}
```

## Breaking Change 管理

### 规则

1. **禁止直接修改现有接口的响应格式**
2. **新增字段必须可选或向后兼容**
3. **删除字段需提前 2 周通知**
4. **版本升级时保持旧版本接口可用**

### 变更日志

所有 API 变更必须记录在：

- `CHANGELOG.md` (版本发布日志)
- OpenAPI 文档的 `info.description` 字段

## CI 集成

### OpenAPI Diff 检查

每次提交时自动对比 OpenAPI 文档：

```yaml
# .github/workflows/api-contract.yml
- name: OpenAPI Diff
  run: |
    python scripts/export_openapi.py
    diff docs/api/openapi.json baseline/openapi.json
```

**失败条件**: 检测到 breaking change 且未在 CHANGELOG 中声明

## 导出 OpenAPI 文档

```bash
cd backend-python
python scripts/export_openapi.py
```

输出文件：
- `docs/api/openapi.json`
- `docs/api/openapi.yaml`

## 在线文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc