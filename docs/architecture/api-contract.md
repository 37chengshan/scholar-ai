# API Contract

## Purpose

统一 ScholarAI API 的路由、响应、错误、分页、鉴权、命名与 SSE 约定，避免接口形态漂移。

## Scope

适用于新的 HTTP/SSE 接口，以及对现有接口的重构与兼容迁移。

## Source of Truth

- 仓库级契约：docs/architecture/api-contract.md
- 后端实现细节：apps/api/docs/API_CONTRACT.md
- 资源生命周期：docs/domain/resources.md

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

## Required Updates

- 新增接口：同步校验是否符合本契约。
- 改动响应格式：同步更新本文件与调用方。
- 改动 SSE 事件：同步更新 docs/architecture/system-overview.md。

## Verification

- 抽样检查新接口响应是否包含 success/data/meta。
- 抽样检查错误路径是否为 RFC 7807。
- 抽样检查分页接口参数与 meta 字段是否一致。
- 抽样检查受保护接口的 401/403 行为。

## Open Questions

- 是否需要统一错误 type 枚举并下沉到共享 SDK。
- 是否将分页从 offset 模式逐步升级到 cursor 模式。
