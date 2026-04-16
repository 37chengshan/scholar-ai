# Schema Inventory

> **来源：** SQLAlchemy ORM 模型（`apps/api/app/models/`）  
> **用途：** Alembic 迁移编写的唯一基准，评审基线  
> **生成时间：** 2026-04-14  
> **冻结点：** 迁移编码前必须以此文档为准，ORM 模型变更需同步更新本文档  

---

## 一、列名引用规范

### 1.1 必须加双引号的标识符

| 类型 | 示例 | 原因 |
|---|---|---|
| camelCase 列名 | `"createdAt"`, `"userId"`, `"paperId"` | PostgreSQL 默认小写，camelCase 需保留大小写 |
| snake_case 保留字 | `"token"`, `"metadata"`, `"type"`, `"key"`, `"role"` | SQL 保留字或易冲突名称 |
| `user` 目录下的其他标识符 | `"id"`, `"name"` 等 | 统一风格，避免歧义 |

### 1.2 无需引号的标识符

- snake_case 普通列名：`storage_key`, `paper_id`, `created_at` 等
- 小写列名：`author`, `title`, `content` 等

### 1.3 列名映射汇总表

#### 1.3.1 Python 属性 → DB 列名（映射不同）

| Python 属性名 | DB 列名 | 表 | 原因 |
|---|---|---|---|
| `token_hash` | `token` | `refresh_tokens` | Prisma schema 约定 |
| `session_metadata` | `metadata` | `sessions` | 避免与 SQLAlchemy 冲突 |
| `extra_data` | `metadata` | `user_memories` | 避免与 SQLAlchemy 保留字冲突 |

#### 1.3.2 camelCase 列名（全部需双引号）

| DB 列名 | 涉及表 |
|---|---|
| `createdAt` | users, papers, paper_chunks, notes, annotations, queries, projects, knowledge_maps |
| `updatedAt` | users, papers, notes, annotations, projects, knowledge_maps |
| `userId` | user_roles, refresh_tokens, papers, notes, annotations, queries, projects, reading_progress, paper_batches, knowledge_maps |
| `roleId` | user_roles |
| `expiresAt` | refresh_tokens |
| `arxivId` | papers |
| `pdfUrl` | papers |
| `pdfPath` | papers |
| `imradJson` | papers |
| `fileSize` | papers |
| `pageCount` | papers |
| `isSearchReady` | papers |
| `isMultimodalReady` | papers |
| `isNotesReady` | papers |
| `notesFailed` | papers |
| `multimodalFailed` | papers |
| `traceId` | papers |
| `pageStart` | paper_chunks |
| `pageEnd` | paper_chunks |
| `isTable` | paper_chunks |
| `isFigure` | paper_chunks |
| `isFormula` | paper_chunks |
| `paperId` | paper_chunks, annotations, reading_progress |
| `queryType` | queries |
| `durationMs` | queries |
| `paperIds` | queries |
| `nodeCount` | knowledge_maps |
| `edgeCount` | knowledge_maps |

#### 1.3.3 SQL 保留字（必须加双引号）

| 列名 | 表 |
|---|---|
| `type` | annotations |
| `key` | configs |
| `role` | chat_messages |
| `token` | refresh_tokens |
| `metadata` | sessions, user_memories |

---

## 二、表定义

---

### 2.1 `users`

**ORM 文件：** `models/user.py`  
**说明：** 用户账户，邮箱/密码认证

| # | Python 属性 | DB 列名 | 类型 | Nullable | Python 默认值 | Server Default | 约束/索引 |
|---|-----------|---------|------|----------|--------------|----------------|-----------|
| 1 | `id` | `id` | `VARCHAR(36)` | No | `uuid.uuid4()` | — | PK |
| 2 | `email` | `email` | `VARCHAR` | No | — | — | UNIQUE |
| 3 | `name` | `name` | `VARCHAR` | No | — | — | — |
| 4 | `password_hash` | `password_hash` | `VARCHAR` | No | — | — | — |
| 5 | `email_verified` | `email_verified` | `BOOLEAN` | No | `False` | — | — |
| 6 | `avatar` | `avatar` | `VARCHAR` | Yes | `None` | — | — |
| 7 | `created_at` | `"createdAt"` | `TIMESTAMP` | No | — | `NOW()` | — |
| 8 | `updated_at` | `"updatedAt"` | `TIMESTAMP` | No | — | `NOW()` | — |

**索引：**

| 索引名 | 列 | 类型 |
|--------|----|------|
| `idx_users_email` | `email` | UNIQUE |

---

### 2.2 `roles`

**ORM 文件：** `models/user.py`  
**说明：** 用户角色定义（admin、user 等）

| # | Python 属性 | DB 列名 | 类型 | Nullable | Python 默认值 | Server Default | 约束/索引 |
|---|-----------|---------|------|----------|--------------|----------------|-----------|
| 1 | `id` | `id` | `VARCHAR(36)` | No | `uuid.uuid4()` | — | PK |
| 2 | `name` | `name` | `VARCHAR` | No | — | — | UNIQUE |
| 3 | `description` | `description` | `VARCHAR` | Yes | `None` | — | — |

**索引：**

| 索引名 | 列 | 类型 |
|--------|----|------|
| `idx_roles_name` | `name` | UNIQUE |

---

### 2.3 `permissions`

**ORM 文件：** `models/user.py`  
**说明：** 权限定义模型

| # | Python 属性 | DB 列名 | 类型 | Nullable | Python 默认值 | Server Default | 约束/索引 |
|---|-----------|---------|------|----------|--------------|----------------|-----------|
| 1 | `id` | `id` | `VARCHAR(36)` | No | `uuid.uuid4()` | — | PK |
| 2 | `resource` | `resource` | `VARCHAR` | No | — | — | — |
| 3 | `action` | `action` | `VARCHAR` | No | — | — | — |

**约束：**

| 约束名 | 列 |
|--------|----|
| `permission_unique` | `resource`, `action` (UNIQUE) |

---

### 2.4 `refresh_tokens`

**ORM 文件：** `models/user.py`  
**说明：** JWT 刷新令牌存储

| # | Python 属性 | DB 列名 | 类型 | Nullable | Python 默认值 | Server Default | 约束/索引 |
|---|-----------|---------|------|----------|--------------|----------------|-----------|
| 1 | `id` | `id` | `VARCHAR(36)` | No | `uuid.uuid4()` | — | PK |
| 2 | `token_hash` | `"token"` | `VARCHAR` | No | — | — | UNIQUE |
| 3 | `user_id` | `"userId"` | `VARCHAR` | No | — | — | FK → users.id |
| 4 | `expires_at` | `"expiresAt"` | `TIMESTAMP WITH TIME ZONE` | No | — | — | — |
| 5 | `created_at` | `"createdAt"` | `TIMESTAMP WITH TIME ZONE` | No | — | `NOW()` | — |

**外键：**

| 列 | 引用 | ON DELETE | ON UPDATE |
|----|------|-----------|-----------|
| `userId` | `users(id)` | CASCADE | CASCADE |

**约束：**

| 约束名 | 列 |
|--------|----|
| `refresh_tokens_token_key` | `token` (UNIQUE) |

---

### 2.5 `user_roles`

**ORM 文件：** `models/user.py`  
**说明：** 用户与角色的多对多关联表

| # | Python 属性 | DB 列名 | 类型 | Nullable | Python 默认值 | Server Default | 约束/索引 |
|---|-----------|---------|------|----------|--------------|----------------|-----------|
| 1 | `id` | `id` | `VARCHAR(36)` | No | `uuid.uuid4()` | — | PK |
| 2 | `user_id` | `"userId"` | `VARCHAR` | No | — | — | FK → users.id |
| 3 | `role_id` | `"roleId"` | `VARCHAR` | No | — | — | FK → roles.id |

**外键：**

| 列 | 引用 | ON DELETE | ON UPDATE |
|----|------|-----------|-----------|
| `userId` | `users(id)` | CASCADE | CASCADE |
| `roleId` | `roles(id)` | CASCADE | CASCADE |

**约束：**

| 约束名 | 列 |
|--------|----|
| `user_role_unique` | `userId`, `roleId` (UNIQUE) |

---

### 2.6 `api_keys`

**ORM 文件：** `models/api_key.py`  
**说明：** 用户 API Key（外部集成认证）

| # | Python 属性 | DB 列名 | 类型 | Nullable | Python 默认值 | Server Default | 约束/索引 |
|---|-----------|---------|------|----------|--------------|----------------|-----------|
| 1 | `id` | `id` | `VARCHAR(36)` | No | `uuid.uuid4()` | — | PK |
| 2 | `user_id` | `user_id` | `VARCHAR` | No | — | — | FK → users.id |
| 3 | `name` | `name` | `VARCHAR` | No | — | — | — |
| 4 | `key_hash` | `key_hash` | `VARCHAR` | No | — | — | — |
| 5 | `prefix` | `prefix` | `VARCHAR` | Yes | `None` | — | — |
| 6 | `created_at` | `created_at` | `TIMESTAMP WITH TIME ZONE` | No | `datetime.now()` | — | — |
| 7 | `last_used_at` | `last_used_at` | `TIMESTAMP WITH TIME ZONE` | Yes | `None` | — | — |

**外键：**

| 列 | 引用 | ON DELETE | ON UPDATE |
|----|------|-----------|-----------|
| `user_id` | `users(id)` | CASCADE | CASCADE |

---

### 2.7 `sessions`

**ORM 文件：** `models/orm_session.py`  
**说明：** 聊天会话（Agent 对话）

| # | Python 属性 | DB 列名 | 类型 | Nullable | Python 默认值 | Server Default | 约束/索引 |
|---|-----------|---------|------|----------|--------------|----------------|-----------|
| 1 | `id` | `id` | `UUID` | No | `str(uuid.uuid4())` | — | PK |
| 2 | `user_id` | `user_id` | `VARCHAR` | No | — | — | FK → users.id, INDEX |
| 3 | `title` | `title` | `VARCHAR(255)` | Yes | `None` | — | — |
| 4 | `status` | `status` | `VARCHAR(50)` | No | `"active"` | — | INDEX |
| 5 | `session_metadata` | `"metadata"` | `JSONB` | Yes | `{}` | — | — |
| 6 | `message_count` | `message_count` | `INTEGER` | No | `0` | — | — |
| 7 | `tool_call_count` | `tool_call_count` | `INTEGER` | No | `0` | — | — |
| 8 | `created_at` | `created_at` | `TIMESTAMP WITH TIME ZONE` | No | — | `NOW()` | — |
| 9 | `updated_at` | `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | — | `NOW()` | — |
| 10 | `last_activity_at` | `last_activity_at` | `TIMESTAMP WITH TIME ZONE` | No | — | `NOW()` | — |
| 11 | `expires_at` | `expires_at` | `TIMESTAMP WITH TIME ZONE` | No | — | — | INDEX |

**外键：**

| 列 | 引用 | ON DELETE | ON UPDATE |
|----|------|-----------|-----------|
| `user_id` | `users(id)` | CASCADE | CASCADE |

**索引：**

| 索引名 | 列 | 类型 |
|--------|----|------|
| `idx_sessions_expires_at` | `expires_at` | B-tree |
| `idx_sessions_status` | `status` | B-tree |
| `idx_sessions_user_id` | `user_id` | B-tree |

---

### 2.8 `audit_logs`

**ORM 文件：** `models/orm_audit_log.py`  
**说明：** 工具执行审计日志

| # | Python 属性 | DB 列名 | 类型 | Nullable | Python 默认值 | Server Default | 约束/索引 |
|---|-----------|---------|------|----------|--------------|----------------|-----------|
| 1 | `id` | `id` | `VARCHAR(36)` | No | `uuid.uuid4()` | — | PK |
| 2 | `user_id` | `user_id` | `VARCHAR` | No | — | — | FK → users.id, INDEX |
| 3 | `tool` | `tool` | `VARCHAR` | No | — | — | — |
| 4 | `risk_level` | `risk_level` | `VARCHAR` | No | — | — | INDEX |
| 5 | `params` | `params` | `JSONB` | Yes | `None` | — | — |
| 6 | `result` | `result` | `TEXT` | Yes | `None` | — | — |
| 7 | `tokens_used` | `tokens_used` | `INTEGER` | Yes | `None` | — | — |
| 8 | `cost_cny` | `cost_cny` | `DOUBLE PRECISION` | Yes | `None` | — | — |
| 9 | `execution_ms` | `execution_ms` | `INTEGER` | Yes | `None` | — | — |
| 10 | `ip_address` | `ip_address` | `VARCHAR` | Yes | `None` | — | — |
| 11 | `created_at` | `created_at` | `TIMESTAMP WITH TIME ZONE` | No | — | `NOW()` | INDEX |

**外键：**

| 列 | 引用 | ON DELETE | ON UPDATE |
|----|------|-----------|-----------|
| `user_id` | `users(id)` | CASCADE | CASCADE |

**索引：**

| 索引名 | 列 | 类型 |
|--------|----|------|
| `idx_audit_logs_user_id` | `user_id` | B-tree |
| `idx_audit_logs_created_at` | `created_at` | B-tree |
| `idx_audit_logs_risk_level` | `risk_level` | B-tree |

---

### 2.9 `papers`

**ORM 文件：** `models/paper.py`  
**说明：** 论文元数据和内容

| # | Python 属性 | DB 列名 | 类型 | Nullable | Python 默认值 | Server Default | 约束/索引 |
|---|-----------|---------|------|----------|--------------|----------------|-----------|
| 1 | `id` | `id` | `VARCHAR(36)` | No | `uuid.uuid4()` | — | PK |
| 2 | `title` | `title` | `VARCHAR` | No | — | — | — |
| 3 | `authors` | `authors` | `TEXT[]` | No | `[]` | — | — |
| 4 | `year` | `year` | `INTEGER` | Yes | `None` | — | — |
| 5 | `abstract` | `abstract` | `TEXT` | Yes | `None` | — | — |
| 6 | `doi` | `doi` | `VARCHAR` | Yes | `None` | — | — |
| 7 | `arxiv_id` | `"arxivId"` | `VARCHAR` | Yes | `None` | — | — |
| 8 | `pdf_url` | `"pdfUrl"` | `VARCHAR` | Yes | `None` | — | — |
| 9 | `pdf_path` | `"pdfPath"` | `VARCHAR` | Yes | `None` | — | — |
| 10 | `content` | `content` | `TEXT` | Yes | `None` | — | — |
| 11 | `imrad_json` | `"imradJson"` | `JSON` | Yes | `None` | — | — |
| 12 | `status` | `status` | `VARCHAR` | No | `"pending"` | — | — |
| 13 | `file_size` | `"fileSize"` | `INTEGER` | Yes | `None` | — | — |
| 14 | `page_count` | `"pageCount"` | `INTEGER` | Yes | `None` | — | — |
| 15 | `keywords` | `keywords` | `TEXT[]` | No | `[]` | — | — |
| 16 | `venue` | `venue` | `VARCHAR` | Yes | `None` | — | — |
| 17 | `citations` | `citations` | `INTEGER` | Yes | `None` | — | — |
| 18 | `created_at` | `"createdAt"` | `TIMESTAMP WITH TIME ZONE` | No | — | `NOW()` | — |
| 19 | `updated_at` | `"updatedAt"` | `TIMESTAMP WITH TIME ZONE` | No | — | `NOW()` | — |
| 20 | `user_id` | `"userId"` | `VARCHAR` | No | — | — | FK → users.id, INDEX |
| 21 | `storage_key` | `storage_key` | `VARCHAR` | Yes | `None` | — | — |
| 22 | `reading_notes` | `reading_notes` | `TEXT` | Yes | `None` | — | — |
| 23 | `notes_version` | `notes_version` | `INTEGER` | No | `0` | — | — |
| 24 | `starred` | `starred` | `BOOLEAN` | No | `False` | — | INDEX |
| 25 | `project_id` | `"projectId"` | `VARCHAR` | Yes | `None` | — | FK → projects.id |
| 26 | `knowledge_base_id` | `knowledge_base_id` | `VARCHAR` | Yes | `None` | — | FK → knowledge_bases.id |
| 27 | `batch_id` | `batch_id` | `VARCHAR` | Yes | `None` | — | FK → paper_batches.id, INDEX |
| 28 | `upload_progress` | `upload_progress` | `INTEGER` | No | `0` | — | — |
| 29 | `upload_status` | `upload_status` | `VARCHAR` | No | `"pending"` | — | — |
| 30 | `uploaded_at` | `uploaded_at` | `TIMESTAMP WITH TIME ZONE` | Yes | `None` | — | — |
| 31 | `is_search_ready` | `"isSearchReady"` | `BOOLEAN` | No | `False` | — | — |
| 32 | `is_multimodal_ready` | `"isMultimodalReady"` | `BOOLEAN` | No | `False` | — | — |
| 33 | `is_notes_ready` | `"isNotesReady"` | `BOOLEAN` | No | `False` | — | — |
| 34 | `notes_failed` | `"notesFailed"` | `BOOLEAN` | No | `False` | — | — |
| 35 | `multimodal_failed` | `"multimodalFailed"` | `BOOLEAN` | No | `False` | — | — |
| 36 | `trace_id` | `"traceId"` | `VARCHAR(36)` | Yes | `None` | — | — |
| 37 | `s2_paper_id` | `s2_paper_id` | `VARCHAR(255)` | Yes | `None` | — | UNIQUE |
| 38 | `citation_count` | `citation_count` | `INTEGER` | No | `0` | — | — |

> **注：** 第 37、38 列（`s2_paper_id`、`citation_count`）在当前 ORM 模型中**缺失定义**，需同步修改 ORM。

**外键：**

| 列 | 引用 | ON DELETE | ON UPDATE |
|----|------|-----------|-----------|
| `userId` | `users(id)` | CASCADE | CASCADE |
| `projectId` | `projects(id)` | SET NULL | CASCADE |
| `knowledge_base_id` | `knowledge_bases(id)` | SET NULL | CASCADE |
| `batch_id` | `paper_batches(id)` | SET NULL | CASCADE |

**约束：**

| 约束名 | 列 |
|--------|----|
| `unique_user_title` | `userId`, `title` (UNIQUE) |
| `idx_papers_s2_paper_id` | `s2_paper_id` (UNIQUE) |

**索引：**

| 索引名 | 列 | 类型 |
|--------|----|------|
| `idx_papers_userId` | `userId` | B-tree |
| `idx_papers_starred` | `starred` | B-tree |
| `idx_papers_batch_id` | `batch_id` | B-tree |
| `idx_papers_s2_paper_id` | `s2_paper_id` | B-tree |
| `idx_papers_citation_count` | `citation_count` | B-tree (DESC) |

---

### 2.10 `paper_chunks`

**ORM 文件：** `models/paper.py`  
**说明：** 论文文本分块（用于 RAG 检索）

| # | Python 属性 | DB 列名 | 类型 | Nullable | Python 默认值 | Server Default | 约束/索引 |
|---|-----------|---------|------|----------|--------------|----------------|-----------|
| 1 | `id` | `id` | `VARCHAR(36)` | No | `uuid.uuid4()` | — | PK |
| 2 | `content` | `content` | `TEXT` | No | — | — | — |
| 3 | `section` | `section` | `VARCHAR` | Yes | `None` | — | — |
| 4 | `page_start` | `"pageStart"` | `INTEGER` | Yes | `None` | — | — |
| 5 | `page_end` | `"pageEnd"` | `INTEGER` | Yes | `None` | — | — |
| 6 | `is_table` | `"isTable"` | `BOOLEAN` | No | `False` | — | — |
| 7 | `is_figure` | `"isFigure"` | `BOOLEAN` | No | `False` | — | — |
| 8 | `is_formula` | `"isFormula"` | `BOOLEAN` | No | `False` | — | — |
| 9 | `created_at` | `"createdAt"` | `TIMESTAMP WITH TIME ZONE` | No | — | `NOW()` | — |
| 10 | `paper_id` | `"paperId"` | `VARCHAR` | No | — | — | FK → papers.id, INDEX |

**外键：**

| 列 | 引用 | ON DELETE | ON UPDATE |
|----|------|-----------|-----------|
| `paperId` | `papers(id)` | CASCADE | CASCADE |

**索引：**

| 索引名 | 列 | 类型 |
|--------|----|------|
| `idx_paper_chunks_paper_id` | `paperId` | B-tree |

**特殊结构（需确认是否现役）：**

- `search_vector tsvector` + GIN 索引 + 触发器（见步骤 1 调研结论）

---

### 2.11 `projects`

**ORM 文件：** `models/project.py`  
**说明：** 用户项目（论文分组管理）

| # | Python 属性 | DB 列名 | 类型 | Nullable | Python 默认值 | Server Default | 约束/索引 |
|---|-----------|---------|------|----------|--------------|----------------|-----------|
| 1 | `id` | `id` | `VARCHAR(36)` | No | `uuid.uuid4()` | — | PK |
| 2 | `user_id` | `"userId"` | `VARCHAR` | No | — | — | FK → users.id, INDEX |
| 3 | `name` | `name` | `VARCHAR` | No | — | — | — |
| 4 | `color` | `color` | `VARCHAR` | No | `"#3B82F6"` | — | — |
| 5 | `created_at` | `"createdAt"` | `TIMESTAMP WITH TIME ZONE` | No | — | `NOW()` | — |
| 6 | `updated_at` | `"updatedAt"` | `TIMESTAMP WITH TIME ZONE` | No | — | `NOW()` | — |

**外键：**

| 列 | 引用 | ON DELETE | ON UPDATE |
|----|------|-----------|-----------|
| `userId` | `users(id)` | CASCADE | CASCADE |

**索引：**

| 索引名 | 列 | 类型 |
|--------|----|------|
| `idx_projects_user_id` | `userId` | B-tree |

---

### 2.12 `knowledge_bases`

**ORM 文件：** `models/knowledge_base.py`  
**说明：** 知识库（增强版 Project，含解析、Embedding、检索配置）

| # | Python 属性 | DB 列名 | 类型 | Nullable | Python 默认值 | Server Default | 约束/索引 |
|---|-----------|---------|------|----------|--------------|----------------|-----------|
| 1 | `id` | `id` | `VARCHAR(36)` | No | `uuid.uuid4()` | — | PK |
| 2 | `user_id` | `user_id` | `VARCHAR` | No | — | — | FK → users.id, INDEX |
| 3 | `name` | `name` | `VARCHAR(50)` | No | — | — | — |
| 4 | `description` | `description` | `VARCHAR(200)` | Yes | `""` | — | — |
| 5 | `category` | `category` | `VARCHAR(50)` | Yes | `"其他"` | — | INDEX |
| 6 | `paper_count` | `paper_count` | `INTEGER` | No | `0` | — | — |
| 7 | `chunk_count` | `chunk_count` | `INTEGER` | No | `0` | — | — |
| 8 | `entity_count` | `entity_count` | `INTEGER` | No | `0` | — | — |
| 9 | `embedding_model` | `embedding_model` | `VARCHAR` | No | `"bge-m3"` | — | — |
| 10 | `parse_engine` | `parse_engine` | `VARCHAR` | No | `"docling"` | — | — |
| 11 | `chunk_strategy` | `chunk_strategy` | `VARCHAR` | No | `"by-paragraph"` | — | — |
| 12 | `enable_graph` | `enable_graph` | `BOOLEAN` | No | `False` | — | — |
| 13 | `enable_imrad` | `enable_imrad` | `BOOLEAN` | No | `True` | — | — |
| 14 | `enable_chart_understanding` | `enable_chart_understanding` | `BOOLEAN` | No | `False` | — | — |
| 15 | `enable_multimodal_search` | `enable_multimodal_search` | `BOOLEAN` | No | `False` | — | — |
| 16 | `enable_comparison` | `enable_comparison` | `BOOLEAN` | No | `False` | — | — |
| 17 | `created_at` | `created_at` | `TIMESTAMP WITH TIME ZONE` | No | — | `NOW()` | — |
| 18 | `updated_at` | `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | — | `NOW()` | — |

**外键：**

| 列 | 引用 | ON DELETE | ON UPDATE |
|----|------|-----------|-----------|
| `user_id` | `users(id)` | CASCADE | CASCADE |

**索引：**

| 索引名 | 列 | 类型 |
|--------|----|------|
| `idx_knowledge_bases_user_id` | `user_id` | B-tree |
| `idx_knowledge_bases_category` | `category` | B-tree |

---

### 2.13 `queries`

**ORM 文件：** `models/query.py`  
**说明：** RAG 问答记录存储

| # | Python 属性 | DB 列名 | 类型 | Nullable | Python 默认值 | Server Default | 约束/索引 |
|---|-----------|---------|------|----------|--------------|----------------|-----------|
| 1 | `id` | `id` | `VARCHAR(36)` | No | `uuid.uuid4()` | — | PK |
| 2 | `question` | `question` | `TEXT` | No | — | — | — |
| 3 | `answer` | `answer` | `TEXT` | Yes | `None` | — | — |
| 4 | `sources` | `sources` | `JSONB` | Yes | `None` | — | — |
| 5 | `query_type` | `"queryType"` | `VARCHAR` | No | `"single"` | — | — |
| 6 | `status` | `status` | `VARCHAR` | No | `"pending"` | — | — |
| 7 | `duration_ms` | `"durationMs"` | `INTEGER` | Yes | `None` | — | — |
| 8 | `created_at` | `"createdAt"` | `TIMESTAMP WITH TIME ZONE` | No | — | `NOW()` | INDEX |
| 9 | `user_id` | `"userId"` | `VARCHAR` | No | — | — | FK → users.id, INDEX |
| 10 | `paper_ids` | `"paperIds"` | `TEXT[]` | No | `[]` | — | — |

**外键：**

| 列 | 引用 | ON DELETE | ON UPDATE |
|----|------|-----------|-----------|
| `userId` | `users(id)` | CASCADE | CASCADE |

**索引：**

| 索引名 | 列 | 类型 |
|--------|----|------|
| `idx_queries_created_at` | `createdAt` | B-tree |
| `idx_queries_user_id` | `userId` | B-tree |

---

### 2.14 `notes`

**ORM 文件：** `models/orm_note.py`  
**说明：** 用户笔记（含论文引用）

| # | Python 属性 | DB 列名 | 类型 | Nullable | Python 默认值 | Server Default | 约束/索引 |
|---|-----------|---------|------|----------|--------------|----------------|-----------|
| 1 | `id` | `id` | `VARCHAR(36)` | No | `uuid.uuid4()` | — | PK |
| 2 | `user_id` | `"userId"` | `VARCHAR` | No | — | — | FK → users.id, INDEX |
| 3 | `title` | `title` | `VARCHAR` | No | — | — | — |
| 4 | `content` | `content` | `TEXT` | No | — | — | — |
| 5 | `tags` | `tags` | `TEXT[]` | No | `[]` | — | — |
| 6 | `paper_ids` | `paper_ids` | `TEXT[]` | No | `[]` | — | — |
| 7 | `created_at` | `"createdAt"` | `TIMESTAMP WITH TIME ZONE` | No | — | `NOW()` | INDEX |
| 8 | `updated_at` | `"updatedAt"` | `TIMESTAMP WITH TIME ZONE` | No | — | `NOW()` | — |

**外键：**

| 列 | 引用 | ON DELETE | ON UPDATE |
|----|------|-----------|-----------|
| `userId` | `users(id)` | CASCADE | CASCADE |

**索引：**

| 索引名 | 列 | 类型 |
|--------|----|------|
| `idx_notes_user_id` | `userId` | B-tree |
| `idx_notes_created_at` | `createdAt` | B-tree |

---

### 2.15 `annotations`

**ORM 文件：** `models/annotation.py`  
**说明：** PDF 标注（高亮、笔记）

| # | Python 属性 | DB 列名 | 类型 | Nullable | Python 默认值 | Server Default | 约束/索引 |
|---|-----------|---------|------|----------|--------------|----------------|-----------|
| 1 | `id` | `id` | `VARCHAR(36)` | No | `uuid.uuid4()` | — | PK |
| 2 | `paper_id` | `"paperId"` | `VARCHAR` | No | — | — | FK → papers.id, INDEX |
| 3 | `user_id` | `"userId"` | `VARCHAR` | No | — | — | FK → users.id, INDEX |
| 4 | `type` | `"type"` | `VARCHAR` | No | — | — | — |
| 5 | `page_number` | `page_number` | `INTEGER` | No | — | — | — |
| 6 | `position` | `position` | `JSONB` | No | — | — | — |
| 7 | `content` | `content` | `TEXT` | Yes | `None` | — | — |
| 8 | `color` | `color` | `VARCHAR` | No | `"#FFEB3B"` | — | — |
| 9 | `created_at` | `"createdAt"` | `TIMESTAMP WITH TIME ZONE` | No | — | `NOW()` | — |
| 10 | `updated_at` | `"updatedAt"` | `TIMESTAMP WITH TIME ZONE` | No | — | `NOW()` | — |

**外键：**

| 列 | 引用 | ON DELETE | ON UPDATE |
|----|------|-----------|-----------|
| `paperId` | `papers(id)` | CASCADE | CASCADE |
| `userId` | `users(id)` | CASCADE | CASCADE |

**索引：**

| 索引名 | 列 | 类型 |
|--------|----|------|
| `idx_annotations_paper_id` | `paperId` | B-tree |
| `idx_annotations_paper_page` | `paperId`, `page_number` | B-tree |
| `idx_annotations_user_id` | `userId` | B-tree |

---

### 2.16 `reading_progress`

**ORM 文件：** `models/reading_progress.py`  
**说明：** 用户在论文上的阅读进度

| # | Python 属性 | DB 列名 | 类型 | Nullable | Python 默认值 | Server Default | 约束/索引 |
|---|-----------|---------|------|----------|--------------|----------------|-----------|
| 1 | `id` | `id` | `VARCHAR(36)` | No | `uuid.uuid4()` | — | PK |
| 2 | `paper_id` | `"paperId"` | `VARCHAR` | No | — | — | FK → papers.id |
| 3 | `user_id` | `"userId"` | `VARCHAR` | No | — | — | FK → users.id, INDEX |
| 4 | `current_page` | `current_page` | `INTEGER` | No | `1` | — | — |
| 5 | `total_pages` | `total_pages` | `INTEGER` | Yes | `None` | — | — |
| 6 | `last_read_at` | `last_read_at` | `TIMESTAMP WITH TIME ZONE` | No | — | `NOW()` | INDEX |

**外键：**

| 列 | 引用 | ON DELETE | ON UPDATE |
|----|------|-----------|-----------|
| `paperId` | `papers(id)` | CASCADE | CASCADE |
| `userId` | `users(id)` | CASCADE | CASCADE |

**约束：**

| 约束名 | 列 |
|--------|----|
| `unique_paper_user` | `paperId`, `userId` (UNIQUE) |

**索引：**

| 索引名 | 列 | 类型 |
|--------|----|------|
| `idx_reading_progress_last_read` | `last_read_at` | B-tree |
| `idx_reading_progress_userId` | `userId` | B-tree |

---

### 2.17 `paper_batches`

**ORM 文件：** `models/batch.py`  
**说明：** 批量上传追踪

| # | Python 属性 | DB 列名 | 类型 | Nullable | Python 默认值 | Server Default | 约束/索引 |
|---|-----------|---------|------|----------|--------------|----------------|-----------|
| 1 | `id` | `id` | `VARCHAR(36)` | No | `uuid.uuid4()` | — | PK |
| 2 | `user_id` | `"userId"` | `VARCHAR` | No | — | — | FK → users.id, INDEX |
| 3 | `total_files` | `total_files` | `INTEGER` | No | — | — | — |
| 4 | `uploaded_count` | `uploaded_count` | `INTEGER` | No | `0` | — | — |
| 5 | `status` | `status` | `VARCHAR` | No | `"uploading"` | — | INDEX |
| 6 | `created_at` | `created_at` | `TIMESTAMP WITH TIME ZONE` | No | — | `NOW()` | — |
| 7 | `updated_at` | `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | — | `NOW()` | — |

**外键：**

| 列 | 引用 | ON DELETE | ON UPDATE |
|----|------|-----------|-----------|
| `userId` | `users(id)` | CASCADE | CASCADE |

**索引：**

| 索引名 | 列 | 类型 |
|--------|----|------|
| `idx_paper_batches_user_id` | `userId` | B-tree |
| `idx_paper_batches_status` | `status` | B-tree |

---

### 2.18 `upload_history`

**ORM 文件：** `models/upload_history.py`  
**说明：** 文件上传历史

| # | Python 属性 | DB 列名 | 类型 | Nullable | Python 默认值 | Server Default | 约束/索引 |
|---|-----------|---------|------|----------|--------------|----------------|-----------|
| 1 | `id` | `id` | `VARCHAR(36)` | No | `uuid.uuid4()` | — | PK |
| 2 | `user_id` | `user_id` | `VARCHAR` | No | — | — | FK → users.id |
| 3 | `paper_id` | `paper_id` | `VARCHAR` | Yes | `None` | — | FK → papers.id |
| 4 | `filename` | `filename` | `VARCHAR` | No | — | — | — |
| 5 | `status` | `status` | `VARCHAR` | No | `"PROCESSING"` | — | — |
| 6 | `chunks_count` | `chunks_count` | `INTEGER` | Yes | `None` | — | — |
| 7 | `llm_tokens` | `llm_tokens` | `INTEGER` | Yes | `None` | — | — |
| 8 | `page_count` | `page_count` | `INTEGER` | Yes | `None` | — | — |
| 9 | `image_count` | `image_count` | `INTEGER` | Yes | `None` | — | — |
| 10 | `table_count` | `table_count` | `INTEGER` | Yes | `None` | — | — |
| 11 | `error_message` | `error_message` | `TEXT` | Yes | `None` | — | — |
| 12 | `processing_time` | `processing_time` | `INTEGER` | Yes | `None` | — | — |
| 13 | `created_at` | `created_at` | `TIMESTAMP WITH TIME ZONE` | No | — | `NOW()` | — |
| 14 | `updated_at` | `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | — | `NOW()` | — |

**外键：**

| 列 | 引用 | ON DELETE | ON UPDATE |
|----|------|-----------|-----------|
| `user_id` | `users(id)` | CASCADE | CASCADE |
| `paper_id` | `papers(id)` | SET NULL | CASCADE |

**索引：**

| 索引名 | 列 | 类型 |
|--------|----|------|
| `idx_upload_history_user_created` | `user_id`, `created_at` | B-tree |

---

### 2.19 `processing_tasks`

**ORM 文件：** `models/task.py`  
**说明：** 异步 PDF 处理任务追踪

| # | Python 属性 | DB 列名 | 类型 | Nullable | Python 默认值 | Server Default | 约束/索引 |
|---|-----------|---------|------|----------|--------------|----------------|-----------|
| 1 | `id` | `id` | `VARCHAR(36)` | No | `uuid.uuid4()` | — | PK |
| 2 | `paper_id` | `paper_id` | `VARCHAR` | No | — | — | FK → papers.id, UNIQUE |
| 3 | `status` | `status` | `VARCHAR` | No | `"pending"` | — | INDEX |
| 4 | `storage_key` | `storage_key` | `VARCHAR` | No | — | — | — |
| 5 | `error_message` | `error_message` | `VARCHAR` | Yes | `None` | — | — |
| 6 | `attempts` | `attempts` | `INTEGER` | No | `0` | — | — |
| 7 | `created_at` | `created_at` | `TIMESTAMP WITH TIME ZONE` | No | — | `NOW()` | — |
| 8 | `updated_at` | `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | — | `NOW()` | — |
| 9 | `completed_at` | `completed_at` | `TIMESTAMP WITH TIME ZONE` | Yes | `None` | — | — |
| 10 | `checkpoint_stage` | `checkpoint_stage` | `VARCHAR(50)` | Yes | `None` | — | — |
| 11 | `checkpoint_storage_key` | `checkpoint_storage_key` | `VARCHAR(255)` | Yes | `None` | — | — |
| 12 | `checkpoint_version` | `checkpoint_version` | `INTEGER` | No | `0` | — | — |
| 13 | `stage_timings` | `stage_timings` | `JSONB` | Yes | `None` | — | — |
| 14 | `failure_stage` | `failure_stage` | `VARCHAR(20)` | Yes | `None` | — | — |
| 15 | `failure_code` | `failure_code` | `VARCHAR(100)` | Yes | `None` | — | — |
| 16 | `failure_message` | `failure_message` | `TEXT` | Yes | `None` | — | — |
| 17 | `is_retryable` | `is_retryable` | `BOOLEAN` | No | `True` | — | — |
| 18 | `trace_id` | `trace_id` | `VARCHAR(36)` | Yes | `None` | — | INDEX |

**外键：**

| 列 | 引用 | ON DELETE | ON UPDATE |
|----|------|-----------|-----------|
| `paper_id` | `papers(id)` | CASCADE | CASCADE |

**约束：**

| 约束名 | 列 |
|--------|----|
| `processing_tasks_paper_id_key` | `paper_id` (UNIQUE) |

**索引：**

| 索引名 | 列 | 类型 |
|--------|----|------|
| `idx_processing_tasks_paper_id` | `paper_id` | B-tree |
| `idx_processing_tasks_status` | `status` | B-tree |
| `idx_processing_tasks_trace_id` | `trace_id` | B-tree |

---

### 2.20 `notes_generation_tasks`

**ORM 文件：** `models/notes_task.py`  
**说明：** 笔记生成任务（独立于 ProcessingTask）

| # | Python 属性 | DB 列名 | 类型 | Nullable | Python 默认值 | Server Default | 约束/索引 |
|---|-----------|---------|------|----------|--------------|----------------|-----------|
| 1 | `id` | `id` | `VARCHAR(36)` | No | `uuid.uuid4()` | — | PK |
| 2 | `paper_id` | `paper_id` | `VARCHAR` | No | — | — | FK → papers.id, UNIQUE |
| 3 | `status` | `status` | `VARCHAR(20)` | No | `"pending"` | — | INDEX |
| 4 | `claimed_by` | `claimed_by` | `VARCHAR(50)` | Yes | `None` | — | — |
| 5 | `claimed_at` | `claimed_at` | `TIMESTAMP WITH TIME ZONE` | Yes | `None` | — | — |
| 6 | `error_message` | `error_message` | `TEXT` | Yes | `None` | — | — |
| 7 | `attempts` | `attempts` | `INTEGER` | No | `0` | — | — |
| 8 | `created_at` | `created_at` | `TIMESTAMP WITH TIME ZONE` | No | — | `NOW()` | — |
| 9 | `completed_at` | `completed_at` | `TIMESTAMP WITH TIME ZONE` | Yes | `None` | — | — |

**外键：**

| 列 | 引用 | ON DELETE | ON UPDATE |
|----|------|-----------|-----------|
| `paper_id` | `papers(id)` | CASCADE | CASCADE |

**约束：**

| 约束名 | 列 |
|--------|----|
| `notes_generation_tasks_paper_id_key` | `paper_id` (UNIQUE) |

**索引：**

| 索引名 | 列 | 类型 |
|--------|----|------|
| `idx_notes_tasks_status` | `status` | B-tree |
| `idx_notes_tasks_paper_id` | `paper_id` | B-tree |

---

### 2.21 `chat_messages`

**ORM 文件：** `models/orm_chat_message.py`  
**说明：** 聊天会话中的消息

| # | Python 属性 | DB 列名 | 类型 | Nullable | Python 默认值 | Server Default | 约束/索引 |
|---|-----------|---------|------|----------|--------------|----------------|-----------|
| 1 | `id` | `id` | `UUID` | No | `str(uuid.uuid4())` | — | PK |
| 2 | `session_id` | `session_id` | `VARCHAR` | No | — | — | FK → sessions.id, INDEX |
| 3 | `role` | `"role"` | `VARCHAR(20)` | No | — | — | — |
| 4 | `content` | `content` | `TEXT` | No | — | — | — |
| 5 | `tool_name` | `tool_name` | `VARCHAR(100)` | Yes | `None` | — | — |
| 6 | `tool_params` | `tool_params` | `JSONB` | Yes | `None` | — | — |
| 7 | `created_at` | `created_at` | `TIMESTAMP WITH TIME ZONE` | No | — | `NOW()` | INDEX |
| 8 | `reasoning_content` | `reasoning_content` | `TEXT` | Yes | `None` | — | — |
| 9 | `current_phase` | `current_phase` | `VARCHAR(50)` | Yes | `None` | — | — |
| 10 | `tool_timeline` | `tool_timeline` | `JSONB` | Yes | `None` | — | — |
| 11 | `citations` | `citations` | `JSONB` | Yes | `None` | — | — |
| 12 | `stream_status` | `stream_status` | `VARCHAR(20)` | Yes | `None` | — | — |
| 13 | `tokens_used` | `tokens_used` | `INTEGER` | Yes | `None` | — | — |
| 14 | `cost` | `cost` | `DOUBLE PRECISION` | Yes | `None` | — | — |
| 15 | `duration_ms` | `duration_ms` | `INTEGER` | Yes | `None` | — | — |

> **注：** 第 8-15 列为 Phase 5.2 预留字段，当前 ORM 模型中已定义但未实际使用。

**外键：**

| 列 | 引用 | ON DELETE | ON UPDATE |
|----|------|-----------|-----------|
| `session_id` | `sessions(id)` | CASCADE | CASCADE |

**索引：**

| 索引名 | 列 | 类型 |
|--------|----|------|
| `idx_chat_messages_created_at` | `created_at` | B-tree |
| `idx_chat_messages_session_id` | `session_id` | B-tree |

---

### 2.22 `token_usage_logs`

**ORM 文件：** `models/token_usage_log.py`  
**说明：** Token 消费追踪

| # | Python 属性 | DB 列名 | 类型 | Nullable | Python 默认值 | Server Default | 约束/索引 |
|---|-----------|---------|------|----------|--------------|----------------|-----------|
| 1 | `id` | `id` | `UUID` | No | — | `gen_random_uuid()` | PK |
| 2 | `user_id` | `user_id` | `VARCHAR` | No | — | — | FK → users.id |
| 3 | `session_id` | `session_id` | `VARCHAR` | Yes | `None` | — | FK → sessions.id, INDEX |
| 4 | `model` | `model` | `VARCHAR(50)` | No | — | — | — |
| 5 | `input_tokens` | `input_tokens` | `INTEGER` | No | — | — | — |
| 6 | `output_tokens` | `output_tokens` | `INTEGER` | No | — | — | — |
| 7 | `total_tokens` | `total_tokens` | `INTEGER` | No | — | — | — |
| 8 | `cost_cny` | `cost_cny` | `DECIMAL` | No | — | — | — |
| 9 | `created_at` | `created_at` | `TIMESTAMP WITH TIME ZONE` | No | — | `NOW()` | — |

**外键：**

| 列 | 引用 | ON DELETE | ON UPDATE |
|----|------|-----------|-----------|
| `user_id` | `users(id)` | CASCADE | CASCADE |
| `session_id` | `sessions(id)` | SET NULL | CASCADE |

**索引：**

| 索引名 | 列 | 类型 |
|--------|----|------|
| `idx_token_usage_session` | `session_id` | B-tree |
| `idx_token_usage_user_date` | `user_id`, `created_at` | B-tree |

---

### 2.23 `user_memories`

**ORM 文件：** `models/user_memory.py`  
**说明：** 用户长期记忆存储（偏好、模式、反馈）

| # | Python 属性 | DB 列名 | 类型 | Nullable | Python 默认值 | Server Default | 约束/索引 |
|---|-----------|---------|------|----------|--------------|----------------|-----------|
| 1 | `id` | `id` | `VARCHAR(36)` | No | `uuid.uuid4()` | — | PK |
| 2 | `user_id` | `user_id` | `VARCHAR` | No | — | — | FK → users.id, INDEX |
| 3 | `content` | `content` | `TEXT` | No | — | — | — |
| 4 | `memory_type` | `memory_type` | `VARCHAR` | No | — | — | INDEX |
| 5 | `extra_data` | `"metadata"` | `JSONB` | Yes | `None` | — | — |
| 6 | `created_at` | `created_at` | `TIMESTAMP WITH TIME ZONE` | No | — | `NOW()` | — |

**外键：**

| 列 | 引用 | ON DELETE | ON UPDATE |
|----|------|-----------|-----------|
| `user_id` | `users(id)` | CASCADE | CASCADE |

**索引：**

| 索引名 | 列 | 类型 |
|--------|----|------|
| `idx_user_memories_user_id` | `user_id` | B-tree |
| `idx_user_memories_memory_type` | `memory_type` | B-tree |

---

### 2.24 `knowledge_maps`

**ORM 文件：** `models/knowledge_map.py`  
**说明：** 知识图谱元数据

| # | Python 属性 | DB 列名 | 类型 | Nullable | Python 默认值 | Server Default | 约束/索引 |
|---|-----------|---------|------|----------|--------------|----------------|-----------|
| 1 | `id` | `id` | `VARCHAR(36)` | No | `uuid.uuid4()` | — | PK |
| 2 | `name` | `name` | `VARCHAR` | No | — | — | — |
| 3 | `description` | `description` | `TEXT` | Yes | `None` | — | — |
| 4 | `domain` | `domain` | `VARCHAR` | Yes | `None` | — | — |
| 5 | `node_count` | `"nodeCount"` | `INTEGER` | No | `0` | — | — |
| 6 | `edge_count` | `"edgeCount"` | `INTEGER` | No | `0` | — | — |
| 7 | `created_at` | `"createdAt"` | `TIMESTAMP WITH TIME ZONE` | No | — | `NOW()` | — |
| 8 | `updated_at` | `"updatedAt"` | `TIMESTAMP WITH TIME ZONE` | No | — | `NOW()` | — |
| 9 | `user_id` | `"userId"` | `VARCHAR` | No | — | — | FK → users.id |

**外键：**

| 列 | 引用 | ON DELETE | ON UPDATE |
|----|------|-----------|-----------|
| `userId` | `users(id)` | CASCADE | CASCADE |

---

### 2.25 `configs`

**ORM 文件：** `models/config.py`  
**说明：** 系统配置键值存储

| # | Python 属性 | DB 列名 | 类型 | Nullable | Python 默认值 | Server Default | 约束/索引 |
|---|-----------|---------|------|----------|--------------|----------------|-----------|
| 1 | `id` | `id` | `VARCHAR(36)` | No | `uuid.uuid4()` | — | PK |
| 2 | `key` | `"key"` | `VARCHAR` | No | — | — | UNIQUE |
| 3 | `value` | `value` | `JSONB` | No | — | — | — |
| 4 | `description` | `description` | `TEXT` | Yes | `None` | — | — |
| 5 | `updated_at` | `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | — | `NOW()` | — |

**约束：**

| 约束名 | 列 |
|--------|----|
| `configs_key_key` | `key` (UNIQUE) |

---

## 三、迁移分组

### 域 A：用户与权限（迁移 006-A）

依赖顺序：`users` → `roles` → `permissions` → `refresh_tokens` → `user_roles` → `api_keys` → `sessions` → `audit_logs`

### 域 B：内容与论文（迁移 006-B）

依赖顺序：`projects` → `knowledge_bases` → `papers` → `annotations` → `queries` → `notes` → `paper_chunks`

> **注：** `paper_chunks` 的 `search_vector` 结构（tsvector + GIN 索引 + 触发器）是否纳入取决于步骤 1 调研结论。

### 域 C：任务与系统（迁移 006-C）

依赖顺序：`processing_tasks` → `notes_generation_tasks` → `reading_progress` → `paper_batches` → `upload_history` → `chat_messages` → `token_usage_logs` → `user_memories` → `knowledge_maps` → `configs`

---

## 四、废弃表（不迁移）

以下 Prisma 多对多连接表在当前 ORM 中无对应实现，不创建：

| 表名 | ORM 替代方案 |
|---|---|
| `_QueryPapers` | `queries.paperIds` (TEXT[] ARRAY 列) |
| `_PermissionToRole` | `user_roles` 中间表 |

---

*最后更新时间：2026-04-14*
