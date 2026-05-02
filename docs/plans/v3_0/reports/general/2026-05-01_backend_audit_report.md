# ScholarAI 后端代码审查报告

**审查范围**: `apps/api/app/` (Python FastAPI 后端)
**审查日期**: 2026-05-01
**代码行数**: 约 250 个 Python 源文件

---

## 一、严重程度汇总

| 严重程度 | 数量 |
|---------|------|
| CRITICAL | 4 |
| HIGH | 7 |
| MEDIUM | 9 |
| LOW | 5 |

---

## 二、CRITICAL 级别问题

### C1. 硬编码 API 密钥泄露到 .env 文件

**文件**: `apps/api/.env` 第 44、58 行

**问题**: `.env` 文件包含真实的 API 密钥，已被 git 跟踪（尽管 `.gitignore` 排除了 `.env`，但文件已存在于工作区）:

```
ZHIPU_API_KEY=0f6ec31f2d784bd49c9d5fad63bfad6a.Me0RBM1adkoOiQc9
SEMANTIC_SCHOLAR_API_KEY=M21X7cAEFkr6R6LwVkhz2MyZFmI0D0UX37gvNDj0
```

**风险**: 如果此文件曾被 commit 过，密钥已暴露。即使 `.gitignore` 排除了 `.env`，密钥仍以明文存储在本地。

**建议**:
1. 立即轮换所有已暴露的 API 密钥
2. 使用 `git filter-branch` 或 `BFG Repo-Cleaner` 清理 git 历史中的密钥
3. 迁移到 secrets manager (如 AWS Secrets Manager, HashiCorp Vault)

---

### C2. JWT 密钥使用弱默认值

**文件**: `apps/api/app/config.py` 第 212 行

```python
JWT_SECRET: str = "test-secret-key-for-development-only"
```

**问题**: 默认 JWT 密钥在代码中硬编码。虽然 `validate_production_settings()` 会检查此值，但:
1. 开发环境仍使用弱密钥，开发环境的 token 可被伪造
2. 如果 `ENVIRONMENT` 未正确设置为 `production`，弱密钥将用于生产

**建议**:
1. 移除默认值，要求通过环境变量提供
2. 启动时强制验证密钥强度 (至少 32 字符随机字符串)

---

### C3. Refresh Token 明文存储

**文件**: `apps/api/app/services/auth_service.py` 第 386-388 行

```python
refresh_token_record = RefreshToken(
    id=refresh_jti,
    token_hash=refresh_token,  # Note: In production, should hash the token
    ...
)
```

**问题**: 代码注释明确承认 refresh token 以明文存储而非哈希。数据库泄露将直接暴露所有用户的 refresh token。

**建议**:
1. 使用 `argon2` 或 `bcrypt` 对 refresh token 进行哈希存储
2. 验证时比较哈希值而非明文

---

### C4. 数据库密码使用弱默认值

**文件**: `apps/api/app/config.py` 第 116、160 行

```python
DATABASE_URL: str = "postgresql://scholarai:scholarai123@localhost:5432/scholarai"
NEO4J_PASSWORD: str = "scholarai123"
```

**问题**: 数据库密码 `scholarai123` 作为默认值硬编码在代码中。虽然生产验证会检查，但开发/测试环境仍使用弱密码。

**建议**: 移除默认密码，强制通过环境变量配置。

---

## 三、HIGH 级别问题

### H1. 文件上传路径遍历风险

**文件**: `apps/api/app/api/uploads.py` 第 225-227 行

```python
storage_key = f"{user_id}/{datetime.now().strftime('%Y%m%d')}/{uuid.uuid4()}.pdf"
local_storage_path = settings.LOCAL_STORAGE_PATH
file_path = os.path.join(local_storage_path, storage_key)
```

**问题**: `storage_key` 使用 `user_id` 作为路径组件。虽然 UUID 格式的 `user_id` 限制了路径遍历，但未对 `LOCAL_STORAGE_PATH` 进行规范化验证。如果配置被篡改，可能导致文件写入任意位置。

**建议**: 添加路径规范化检查，确保 `file_path` 仍在 `LOCAL_STORAGE_PATH` 下。

---

### H2. SSE 错误响应返回 200 状态码

**文件**: `apps/api/app/api/rag.py` 第 675 行
**文件**: `apps/api/app/api/chat.py` 第 700 行

```python
return StreamingResponse(
    error_stream(),
    media_type="text/event-stream",
    status_code=status.HTTP_200_OK  # 错误时仍返回 200
)
```

**问题**: 流式响应在发生错误时仍返回 HTTP 200，错误信息仅通过 SSE event 传递。这违反了 HTTP 语义，前端难以正确处理错误。

**建议**: 使用适当的 HTTP 状态码 (如 207 Multi-Status 或在 headers 中指示错误)。

---

### H3. 缺少请求体大小限制

**文件**: `apps/api/app/api/chat.py` 第 83、134 行

**问题**: Chat 端点接收 JSON 请求体，但未对 `message` 字段长度进行限制。恶意用户可发送超大消息导致内存耗尽。

**建议**: 在 `ChatStreamRequest` 模型中添加 `max_length` 约束。

---

### H4. `forgot_password` 接受任意 dict 作为请求体

**文件**: `apps/api/app/api/auth.py` 第 573-577 行

```python
@router.post("/forgot-password", response_model=AuthResponse)
async def forgot_password(
    request: Request,
    body: dict,  # 未使用 Pydantic 模型
):
```

**问题**: 使用原始 `dict` 而非 Pydantic 模型，绕过了请求验证。

**建议**: 定义 `ForgotPasswordRequest` Pydantic 模型。

---

### H5. N+1 查询模式

**文件**: `apps/api/app/services/auth_service.py` 第 253-255 行

```python
roles = await get_user_roles(user_id, session if not should_commit else None)
```

**问题**: `register_user` 在创建用户后单独查询角色。`get_user_by_id`、`get_user_by_email` 等函数也都单独查询角色，导致 N+1 查询。

**建议**: 使用 SQLAlchemy 的 `joinedload` 或 `selectinload` 预加载关系。

---

### H6. 日志中记录敏感信息

**文件**: `apps/api/app/api/auth.py` 第 262-267 行

```python
logger.info(
    "User registered",
    user_id=user.id,
    email=user.email,  # 邮箱记录到日志
    request_id=request_id,
)
```

**问题**: 日志中记录用户邮箱，可能违反 GDPR 等隐私法规。

**建议**: 日志中对邮箱进行脱敏处理 (如 `u***@example.com`)。

---

### H7. 缺少速率限制的全局配置

**文件**: `apps/api/app/config.py` 第 110-111 行

```python
RATE_LIMIT_ENABLED: bool = True
RATE_LIMIT_DEFAULT_PER_HOUR: int = 200
```

**问题**: 虽然定义了速率限制配置，但仅在 `auth.py` 中实现了认证端点的速率限制。其他 API 端点 (如 RAG 查询、文件上传) 没有速率限制，容易被滥用。

**建议**: 实现全局速率限制中间件。

---

## 四、MEDIUM 级别问题

### M1. 文件超过 800 行限制

**文件**:
- `apps/api/app/api/chat.py` (911 行)
- `apps/api/app/api/rag.py` (990 行)
- `apps/api/app/api/uploads.py` (1075 行)

**问题**: 多个文件超过项目规范的 800 行限制，职责不够单一。

**建议**: 拆分为更小的模块 (如将 SSE 生成逻辑提取为独立服务)。

---

### M2. Session 消息存储在 metadata JSON 中

**文件**: `apps/api/app/api/rag.py` 第 960-985 行

```python
metadata = session.metadata or {}
messages = metadata.get("messages", [])
messages.append({"role": "user", "content": request.question, "timestamp": now})
```

**问题**: 对话消息存储在 Session 的 `metadata` JSON 字段中，而非独立的 messages 表。这导致:
1. 无法高效查询历史消息
2. JSON 字段随消息增长而膨胀
3. 无法建立消息索引

**建议**: 使用独立的 `messages` 表，通过 `session_id` 关联。

---

### M3. 时间戳使用不一致

**文件**: `apps/api/app/api/rag.py` 第 965 行

```python
now = datetime.utcnow().isoformat()  # deprecated
```

**问题**: 使用已弃用的 `datetime.utcnow()`，而其他地方使用 `datetime.now(timezone.utc)`。

**建议**: 统一使用 `datetime.now(timezone.utc)`。

---

### M4. 缺少数据库迁移管理

**文件**: `apps/api/app/database.py` 第 250-279 行

**问题**: `ensure_non_production_tables` 在非生产环境自动创建表，但没有使用 Alembic 迁移。这可能导致 schema 不一致。

**建议**: 所有环境统一使用 Alembic 迁移管理。

---

### M5. 重复的错误响应创建代码

**文件**: 多个 API 路由文件

**问题**: `_create_error_response` 函数在 `auth.py`、`uploads.py` 等多个文件中重复定义。

**建议**: 提取到 `app/utils/problem_detail.py` 作为公共工具函数。

---

### M6. 缺少输入消毒

**文件**: `apps/api/app/api/auth.py` 第 103-113 行

```python
class RegisterRequest(BaseModel):
    email: str
    password: str = Field(..., min_length=8)
    name: str = Field(..., min_length=2, max_length=50)
```

**问题**: `name` 字段仅验证长度，未对特殊字符或 HTML 标签进行过滤，可能存在存储型 XSS 风险。

**建议**: 添加 `strip()` 和字符白名单验证。

---

### M7. CORS 配置过于宽松

**文件**: `apps/api/app/middleware/cors.py` 第 93-99 行

```python
"allow_methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
```

**问题**: 允许所有标准 HTTP 方法，但部分端点可能只需要特定方法。

**建议**: 按路由组限制允许的方法。

---

### M8. 数据库连接池配置固定

**文件**: `apps/api/app/database.py` 第 60-68 行

```python
engine = create_async_engine(
    settings.async_database_url,
    pool_size=20,
    max_overflow=0,
    ...
)
```

**问题**: 连接池参数硬编码，无法通过环境变量配置。

**建议**: 将 `pool_size`、`max_overflow` 等参数移至 `Settings`。

---

### M9. 缺少请求 ID 传播

**文件**: `apps/api/app/middleware/observability.py` (推断)

**问题**: 虽然定义了 `X-Request-ID` header，但在错误响应中未始终包含此 ID，难以追踪问题。

**建议**: 确保所有响应都包含 `X-Request-ID`。

---

## 五、LOW 级别问题

### L1. 未使用的导入

**文件**: `apps/api/app/api/rag.py` 第 15 行

```python
from fastapi.responses import StreamingResponse  # 在 rag_query 中未使用
```

---

### L2. Magic Numbers

**文件**: `apps/api/app/api/rag.py` 第 976 行

```python
if len(messages) > 20:  # 为什么是 20?
```

**建议**: 定义为常量 `MAX_CONVERSATION_MESSAGES = 20`。

---

### L3. 文档字符串不完整

**文件**: 多个文件

**问题**: 部分函数缺少返回值说明或异常说明。

---

### L4. 测试覆盖率信息缺失

**问题**: 虽然有 250 个测试文件，但没有覆盖率报告配置。

**建议**: 在 `pytest.ini` 中添加 `--cov` 配置。

---

### L5. 依赖版本未锁定

**文件**: `apps/api/requirements.txt`

**问题**: 大部分依赖使用范围版本 (`>=x.y.z`) 而非精确版本，可能导致构建不可重复。

**建议**: 使用 `pip freeze` 生成 `requirements.lock` 文件。

---

## 六、架构建议

1. **依赖注入**: 考虑使用 `dependency-injector` 或类似库统一管理服务依赖
2. **API 版本控制**: 当前使用 `/api/v1/` 前缀，建议明确版本迁移策略
3. **文档**: OpenAPI 文档应补充所有端点的错误响应说明
4. **监控**: 建议集成 Prometheus metrics 端点

---

## 七、优先修复建议

| 优先级 | 问题 | 预计工作量 |
|--------|------|-----------|
| P0 | C1 - 轮换泄露的 API 密钥 | 2h |
| P0 | C2 - 强制 JWT 密钥配置 | 1h |
| P0 | C3 - 哈希存储 refresh token | 4h |
| P1 | H2 - 修复 SSE 错误状态码 | 2h |
| P1 | H7 - 全局速率限制 | 4h |
| P2 | M2 - 独立 messages 表 | 8h |
| P2 | M5 - 消除重复代码 | 4h |
