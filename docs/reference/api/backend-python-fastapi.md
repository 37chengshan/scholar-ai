# FastAPI 后端接口列表

ScholarAI 统一后端 API，Port 8000，基于 FastAPI 构建。

---

## 认证相关 `/api/v1/auth`

| 方法 | 路径 | 功能 | 请求体 | 响应 | 认证 |
|------|------|------|--------|------|------|
| POST | `/api/v1/auth/register` | 用户注册 | `{email, password, name}` | `{user, meta}` | 否 |
| POST | `/api/v1/auth/login` | 用户登录 (OAuth2表单) | `username=email, password` | `{user, meta}` + 设置 httpOnly cookies | 否 |
| POST | `/api/v1/auth/refresh` | 刷新 Access Token | 可选 `{refresh_token}` | `{message, meta}` | 否 |
| POST | `/api/v1/auth/logout` | 登出并黑名单 Token | - | `{message, meta}` | 是 |
| GET | `/api/v1/auth/me` | 获取当前用户信息 | - | `{user, meta}` | 是 |
| POST | `/api/v1/auth/forgot-password` | 请求密码重置邮件 | `{email}` | `{message}` | 否 |

---

## 用户管理 `/api/v1/users`

| 方法 | 路径 | 功能 | 请求体 | 响应 | 认证 |
|------|------|------|--------|------|------|
| GET | `/api/v1/users/me` | 获取当前用户资料 | - | `{id, email, name, avatar, email_verified}` | 是 |
| PATCH | `/api/v1/users/me` | 更新用户资料 | `{name?, email?, avatar?}` | `{id, email, name, avatar}` | 是 |
| POST | `/api/v1/users/me/avatar` | 上传头像 | `file (JPEG/PNG/WebP, max 5MB)` | `{avatar: url}` | 是 |
| PATCH | `/api/v1/users/me/password` | 修改密码 | `{current_password, new_password}` | `{message}` | 是 |
| GET | `/api/v1/users/me/settings` | 获取用户设置 | - | `{language, defaultModel, theme}` | 是 |
| PATCH | `/api/v1/users/me/settings` | 更新用户设置 | `{language?, defaultModel?, theme?}` | `{...settings}` | 是 |
| GET | `/api/v1/users/me/api-keys` | 列出 API Keys | - | `[{id, name, prefix, createdAt, lastUsedAt}]` | 是 |
| POST | `/api/v1/users/me/api-keys` | 创建 API Key | `{name}` | `{id, name, prefix, createdAt, key}` | 是 |
| DELETE | `/api/v1/users/me/api-keys/{key_id}` | 删除 API Key | - | `{message}` | 是 |

---

## 论文管理 `/api/v1/papers`

| 方法 | 路径 | 功能 | 请求体 | 响应 | 认证 |
|------|------|------|--------|------|------|
| GET | `/api/v1/papers/` | 列出论文 (分页+过滤) | Query: `page, limit, starred, readStatus, dateFrom, dateTo` | `{papers[], total, page, limit, totalPages}` | 是 |
| GET | `/api/v1/papers/search` | 搜索论文 | Query: `q, page, limit` | `{papers[], total, query}` | 是 |
| POST | `/api/v1/papers/` | 创建论文记录 (获取上传URL) | `{filename}` | `{paperId, uploadUrl, storageKey, expiresIn}` | 是 |
| GET | `/api/v1/papers/{paper_id}` | 获取论文详情 | Query: `includeChunks?` | `{...paper}` | 是 |
| PATCH | `/api/v1/papers/{paper_id}` | 更新论文元数据 | `{title?, authors?, year?, abstract?, keywords?, starred?, projectId?, readingNotes?}` | `{...paper}` | 是 |
| DELETE | `/api/v1/papers/{paper_id}` | 删除论文 | - | `{message}` | 是 |
| POST | `/api/v1/papers/batch-delete` | 批量删除论文 | `{paper_ids[]}` | `{deletedCount, requestedCount, message}` | 是 |
| POST | `/api/v1/papers/batch/star` | 批量标记论文 | `{paper_ids[], starred}` | `{updatedCount, starred, message}` | 是 |
| GET | `/api/v1/papers/{paper_id}/status` | 获取处理状态 | - | `{paperId, status, progress, stage, errorMessage}` | 是 |
| PATCH | `/api/v1/papers/{paper_id}/starred` | 切换星标状态 | `{starred: bool}` | `{success, ...paper}` | 是 |
| GET | `/api/v1/papers/{paper_id}/download` | 下载 PDF | - | `FileResponse (application/pdf)` | 是 |
| GET | `/api/v1/papers/{paper_id}/chunks` | 获取论文分块 | - | `{id, content, section, page_start, page_end, is_table, is_figure}[]` | 是 |
| POST | `/api/v1/papers/{paper_id}/regenerate-chunks` | 重新生成分块 | - | `{taskId, message}` | 是 |
| GET | `/api/v1/papers/{paper_id}/summary` | 获取论文摘要和笔记 | - | `{paperId, summary, imrad, status, hasNotes}` | 是 |
| POST | `/api/v1/papers/{paper_id}/regenerate-notes` | 重新生成笔记 | `{modificationRequest?}` | `{paperId, status, message}` | 是 |
| GET | `/api/v1/papers/{paper_id}/notes/export` | 导出笔记为 Markdown | - | `PlainTextResponse (text/markdown)` | 是 |
| POST | `/api/v1/papers/upload/webhook` | 确认上传完成 (Webhook) | `{paperId, storageKey}` | `{taskId, paperId, status, progress}` | 是 |
| POST | `/api/v1/papers/upload` | 直接文件上传 | `file (PDF, max 50MB)` | `{paperId, taskId, status}` | 是 |
| POST | `/api/v1/papers/upload/local/{storage_key}` | 上传文件到本地存储 | `file (PDF)` | `{storageKey, size, message}` | 是 |

---

## 上传管理 `/api/v1/uploads`

| 方法 | 路径 | 功能 | 请求体 | 响应 | 认证 |
|------|------|------|--------|------|------|
| POST | `/api/v1/uploads` | 单文件上传 | `file (PDF, max 50MB)` | `{paperId, taskId, status, message}` | 是 |
| POST | `/api/v1/uploads/batch` | 创建批量上传会话 | `{files: [{filename, fileSize, title?, doi?}]}` | `{batchId, totalFiles, papers[]}` | 是 |
| GET | `/api/v1/uploads/batch/{batch_id}` | 获取批量状态 | - | `{id, total_files, uploaded_count, status}` | 是 |
| GET | `/api/v1/uploads/batch/{batch_id}/progress` | 获取批量进度 | - | `{batchId, totalFiles, papers[], overallProgress}` | 是 |
| POST | `/api/v1/uploads/batch/{batch_id}/files` | 上传文件到批量 | `file (PDF)` | `{paperId, uploadedCount, totalFiles}` | 是 |
| GET | `/api/v1/uploads/history` | 获取上传历史 | Query: `limit, offset` | `{records[], total, limit, offset}` | 是 |
| GET | `/api/v1/uploads/history/{upload_id}` | 获取单条上传历史 | - | `{...record}` | 是 |
| POST | `/api/v1/uploads/history` | 记录外部URL上传 | `{url, title, source?}` | `{uploadId, message}` | 是 |
| DELETE | `/api/v1/uploads/history/{upload_id}` | 删除上传历史 | - | `{message, paperPreserved}` | 是 |

---

## 任务管理 `/api/v1/tasks`

| 方法 | 路径 | 功能 | 请求体 | 响应 | 认证 |
|------|------|------|--------|------|------|
| GET | `/api/v1/tasks` | 列出任务 | Query: `paperId?, status?, limit, offset` | `{tasks[], total, limit, offset}` | 是 |
| GET | `/api/v1/tasks/{task_id}` | 获取任务详情 | - | `{id, paper_id, status, storage_key, ...}` | 是 |
| POST | `/api/v1/tasks/{task_id}/retry` | 重试失败任务 | - | `{taskId, status, message}` | 是 |
| GET | `/api/v1/tasks/{task_id}/progress` | 获取详细进度 | - | `{taskId, paperId, stages[], progress, ...}` | 是 |
| DELETE | `/api/v1/tasks/{task_id}` | 取消待处理任务 | - | `{message, taskId}` | 是 |

---

## 笔记 `/api/v1/notes`

| 方法 | 路径 | 功能 | 请求体 | 响应 | 认证 |
|------|------|------|--------|------|------|
| GET | `/api/v1/notes` | 列出笔记 (过滤+分页) | Query: `paperId?, tag?, sortBy, order, limit, offset` | `{notes[], total, limit, offset}` | 是 |
| POST | `/api/v1/notes` | 创建笔记 | `{title, content, tags?, paperIds?}` | `{...note}` | 是 |
| GET | `/api/v1/notes/{note_id}` | 获取笔记详情 | - | `{...note}` | 是 |
| PUT | `/api/v1/notes/{note_id}` | 更新笔记 | `{title?, content?, tags?, paperIds?}` | `{...note}` | 是 |
| DELETE | `/api/v1/notes/{note_id}` | 删除笔记 | - | `204 No Content` | 是 |
| GET | `/api/v1/notes/paper/{paper_id}` | 获取论文关联笔记 | - | `{notes[], total}` | 是 |
| POST | `/api/v1/notes/generate` | AI 生成论文笔记 | `{paperId}` | `{paperId, notes, version}` | 是 |
| POST | `/api/v1/notes/regenerate` | 重新生成笔记 | `{paperId, modificationRequest}` | `{paperId, notes, version}` | 是 |
| GET | `/api/v1/notes/{paper_id}/export` | 导出笔记为 Markdown | - | `{paperId, markdown, version, filename}` | 是 |

---

## 项目 `/api/v1/projects`

| 方法 | 路径 | 功能 | 请求体 | 响应 | 认证 |
|------|------|------|--------|------|------|
| GET | `/api/v1/projects` | 列出项目 | - | `[{id, name, color, paperCount, ...}]` | 是 |
| POST | `/api/v1/projects` | 创建项目 | `{name, color?}` | `{...project}` | 是 |
| GET | `/api/v1/projects/{project_id}` | 获取项目详情 | - | `{...project}` | 是 |
| PATCH | `/api/v1/projects/{project_id}` | 更新项目 | `{name?, color?}` | `{...project}` | 是 |
| DELETE | `/api/v1/projects/{project_id}` | 删除项目 | - | `{id, deleted}` | 是 |
| PATCH | `/api/v1/projects/paper/{paper_id}` | 分配论文到项目 | `{projectId?}` | `{id, title, projectId}` | 是 |

---

## 标注 `/api/v1/annotations`

| 方法 | 路径 | 功能 | 请求体 | 响应 | 认证 |
|------|------|------|--------|------|------|
| GET | `/api/v1/annotations/{paper_id}` | 列出论文标注 | - | `[{id, paper_id, type, page_number, position, content, color, ...}]` | 是 |
| POST | `/api/v1/annotations` | 创建标注 | `{paperId, type, pageNumber, position, content?, color?}` | `{id, paper_id, type, ...}` | 是 |
| PATCH | `/api/v1/annotations/{annotation_id}` | 更新标注 | `{content?, color?}` | `{id, paper_id, type, ...}` | 是 |
| DELETE | `/api/v1/annotations/{annotation_id}` | 删除标注 | - | `{id, deleted}` | 是 |

---

## 阅读进度 `/api/v1/reading-progress`

| 方法 | 路径 | 功能 | 请求体 | 响应 | 认证 |
|------|------|------|--------|------|------|
| GET | `/api/v1/reading-progress` | 列出所有阅读进度 | - | `[{id, paper_id, current_page, total_pages, progress, title, ...}]` | 是 |
| GET | `/api/v1/reading-progress/{paper_id}` | 获取论文阅读进度 | - | `{paper_id, current_page, total_pages, last_read_at}` | 是 |
| POST | `/api/v1/reading-progress/{paper_id}` | 创建/更新阅读进度 | `{currentPage, totalPages?}` | `{id, paper_id, current_page, ...}` | 是 |

---

## 知识库 `/api/v1/knowledge-bases`

| 方法 | 路径 | 功能 | 请求体 | 响应 | 认证 |
|------|------|------|--------|------|------|
| GET | `/api/v1/knowledge-bases/` | 列出知识库 | Query: `search?, category?, sortBy, order, limit, offset` | `{knowledgeBases[], total, limit, offset}` | 是 |
| POST | `/api/v1/knowledge-bases/` | 创建知识库 | `{name, description?, category?, embeddingModel?, parseEngine?, chunkStrategy?, enableGraph?, enableImrad?, enableChartUnderstanding?, enableMultimodalSearch?, enableComparison?}` | `{...kb}` | 是 |
| GET | `/api/v1/knowledge-bases/{kb_id}` | 获取知识库详情 | - | `{...kb}` | 是 |
| PATCH | `/api/v1/knowledge-bases/{kb_id}` | 更新知识库 | `{name?, description?, category?}` | `{...kb}` | 是 |
| DELETE | `/api/v1/knowledge-bases/{kb_id}` | 删除知识库 | - | `{id, deleted}` | 是 |
| POST | `/api/v1/knowledge-bases/batch-delete` | 批量删除知识库 | `{ids[]}` | `{deletedIds[], count}` | 是 |
| POST | `/api/v1/knowledge-bases/batch-export` | 批量导出知识库 | `{ids[]}` | `{knowledgeBases[], count}` | 是 |
| GET | `/api/v1/knowledge-bases/storage-stats` | 获取存储统计 | - | `{kbCount, paperCount, chunkCount, estimatedStorageMB}` | 是 |
| POST | `/api/v1/knowledge-bases/{kb_id}/upload` | 上传 PDF 到知识库 | `file (PDF)` | `{kbId, paperId, taskId, status, message}` | 是 |
| POST | `/api/v1/knowledge-bases/{kb_id}/import-url` | 从 URL/DOI 导入 | `{url}` | `{message, url}` | 是 | ⚠️ Stub |
| POST | `/api/v1/knowledge-bases/{kb_id}/import-arxiv` | 从 arXiv 导入 | `{arxivId}` | `{message, arxivId}` | 是 | ⚠️ Stub |
| POST | `/api/v1/knowledge-bases/{kb_id}/batch-upload` | 批量上传 | - | `{message, kbId}` | 是 | ⚠️ Stub |
| GET | `/{kb_id}/upload-history` | 获取上传历史 | Query: `limit, offset` | `{records[], total}` | 是 |
| DELETE | `/{kb_id}/upload-history/{history_id}` | 删除上传历史 | - | `{id, deleted}` | 是 |
| GET | `/{kb_id}/papers` | 列出 KB 内论文 | Query: `limit, offset` | `{papers[], total, limit, offset}` | 是 | |
| POST | `/{kb_id}/papers` | 添加论文到 KB | `{paperId}` | `{paperId, knowledgeBaseId, paperCount}` | 是 | |
| DELETE | `/{kb_id}/papers/{paper_id}` | 从 KB 移除论文 | - | `{paperId, removed, paperCount}` | 是 | |
| POST | `/{kb_id}/query` | KB 内部 RAG 问答 | `{query, topK?}` | `{answer, citations[], sources[], confidence}` | 是 | |

---

## 导入任务 `/api/v1`

| 方法 | 路径 | 功能 | 请求体 | 响应 | 认证 |
|------|------|------|--------|------|------|
| POST | `/knowledge-bases/{kb_id}/imports` | 创建导入任务 | `{sourceType, payload, options?}` | `{importJobId, knowledgeBaseId, status, stage, progress, nextAction}` | 是 |
| PUT | `/import-jobs/{job_id}/file` | 上传 PDF 到导入任务 | `file (PDF)` | `{importJobId, status, file:{storageKey, sha256, sizeBytes}}` | 是 |
| GET | `/import-jobs/{job_id}` | 获取导入任务状态 | - | `{importJobId, sourceType, status, stage, progress, preview, dedupe, paper, task, error?}` | 是 |
| GET | `/import-jobs` | 列出导入任务 | Query: `knowledgeBaseId?, status?, limit, offset` | `{jobs[], total, limit, offset}` | 是 |
| POST | `/import-jobs/{job_id}/retry` | 重试失败任务 | `{retryFromStage?}` | `{importJobId, status, retryCount}` | 是 |
| POST | `/import-jobs/{job_id}/cancel` | 取消导入任务 | - | `{importJobId, status, cancelledAt}` | 是 |
| GET | `/import-jobs/{job_id}/stream` | SSE 进度流 | - | `text/event-stream` | 是 |
| POST | `/import-sources/resolve` | 解析单一来源 | `{input, sourceType?}` | `{success, data: {resolved, normalizedSource, preview, availability}}` | 是 |
| POST | `/import-sources/resolve-batch` | 批量解析来源 | `{items[]}` | `{success, data: {items[], total, resolvedCount}}` | 是 |
| POST | `/import-jobs/{job_id}/dedupe-decision` | 提交去重决策 | `{decision, matchedPaperId?}` | `{importJobId, status, action}` | 是 |
| GET | `/import-batches/{batch_id}` | 获取批量导入状态 | - | `{batchJobId, status, summary: {total, running, completed, failed, cancelled}, items[]}` | 是 |
| POST | `/knowledge-bases/{kb_id}/imports/batch` | 创建批量导入任务 | `{items[], options?}` | `{batchJobId, status, totalItems, items[]}` | 是 |

---

## 仪表盘 `/api/v1/dashboard`

| 方法 | 路径 | 功能 | 请求体 | 响应 | 认证 |
|------|------|------|--------|------|------|
| GET | `/api/v1/dashboard/stats` | 获取统计概览 | - | `{totalPapers, starredPapers, processingPapers, completedPapers, queriesCount, sessionsCount, projectsCount, llmTokens}` | 是 |
| GET | `/api/v1/dashboard/trends` | 获取趋势数据 | Query: `period (weekly/monthly)` | `{dataPoints: [{date, papers, queries}], period}` | 是 |
| GET | `/api/v1/dashboard/recent-papers` | 获取最近阅读 | Query: `limit (1-20)` | `[{id, title, authors, year, status, currentPage, progress, ...}]` | 是 |
| GET | `/api/v1/dashboard/reading-stats` | 获取阅读统计 | - | `{totalPapersWithProgress, totalPagesRead, completedPapers, averageProgress}` | 是 |

---

## 搜索 `/api/v1/search`

| 方法 | 路径 | 功能 | 请求体 | 响应 | 认证 |
|------|------|------|--------|------|------|
| GET | `/api/v1/search/arxiv` | 搜索 arXiv | Query: `query, limit, offset` | `{results: [{id, title, authors, year, abstract, source, pdfUrl, ...}], total}` | 否 |
| GET | `/api/v1/search/semantic-scholar` | 搜索 Semantic Scholar | Query: `query, limit, offset` | `{results: [{id, title, authors, year, abstract, source, pdfUrl, citationCount, ...}], total}` | 否 |
| GET | `/api/v1/search/unified` | 统一搜索 (合并) | Query: `query, limit, offset, year_from?, year_to?` | `{results: [...], total}` | 否 |
| GET | `/api/v1/search/library` | 搜索个人文献库 (Milvus) | Query: `q, paper_ids[], limit` | `{query, paperCount, results: [{id, paper_id, content, section, rrfScore, ...}]}` | 是 |
| POST | `/api/v1/search/fusion` | 融合搜索 | `{query, paper_ids[], limit?, sources?}` | `{query, results[], sources: {...}, warnings?}` | 是 |
| POST | `/api/v1/search/multimodal` | 多模态搜索 | `{query, paper_ids[], top_k?, use_reranker?, content_types?, enable_clustering?}` | `{query, intent, clusters?, results[], totalCount}` | 是 |
| GET | `/search/doi/{doi}` | 解析 DOI | Path: `doi` | `{success, data: {...}}` | 否 |

---

## Semantic Scholar

| 方法 | 路径 | 功能 | 请求体 | 响应 | 认证 |
|------|------|------|--------|------|------|
| POST | `/api/v1/semantic-scholar/batch` | 批量获取论文 | `{ids[]}` | `[...]` | 否 |
| GET | `/api/v1/semantic-scholar/paper/{paper_id}` | 获取论文详情 | Query: `fields?` | `{...}` | 否 |
| GET | `/api/v1/semantic-scholar/paper/{paper_id}/citations` | 获取引用 (施引) | Query: `fields?, limit?` | `[...]` | 否 |
| GET | `/api/v1/semantic-scholar/paper/{paper_id}/references` | 获取参考文献 (被引) | Query: `fields?, limit?` | `[...]` | 否 |
| GET | `/api/v1/semantic-scholar/autocomplete` | 论文自动补全 | Query: `query, limit (1-20)` | `[...]` | 否 |
| GET | `/api/v1/semantic-scholar/author/search` | 搜索作者 | Query: `query, limit, offset` | `{...}` | 否 |
| GET | `/api/v1/semantic-scholar/author/{author_id}/papers` | 获取作者论文 | Query: `limit, offset` | `{...}` | 否 |

---

## 会话 `/api/v1/sessions`

| 方法 | 路径 | 功能 | 请求体 | 响应 | 认证 |
|------|------|------|--------|------|------|
| POST | `/api/v1/sessions` | 创建会话 | `{title?}` | `{id, userId, title, status, messageCount, ...}` | 是 |
| GET | `/api/v1/sessions` | 列出会话 | Query: `limit, status` | `{sessions[], total, limit}` | 是 |
| GET | `/api/v1/sessions/{session_id}` | 获取会话详情 | - | `{...session}` | 是 |
| PATCH | `/api/v1/sessions/{session_id}` | 更新会话 | `{title?, status?, metadata?}` | `{...session}` | 是 |
| DELETE | `/api/v1/sessions/{session_id}` | 删除会话 | - | `204 No Content` | 是 |
| GET | `/api/v1/sessions/{session_id}/messages` | 获取会话消息 | Query: `limit, offset` | `{session_id, messages[], total, limit}` | 是 |

---

## 聊天 `/api/v1/chat`

| 方法 | 路径 | 功能 | 请求体 | 响应 | 认证 |
|------|------|------|--------|------|------|
| POST | `/api/v1/chat/stream` | SSE 流式聊天 | `{message, session_id?, context?}` | `text/event-stream` | 是 |
| POST | `/api/v1/chat/confirm` | 确认危险操作 | `{confirmation_id, session_id, approved}` | `text/event-stream` | 是 |

SSE 事件类型: `routing_decision`, `thought`, `tool_call`, `tool_result`, `confirmation_required`, `message`, `error`, `done`

---

## 实体与知识图谱 `/api/v1/entities`

| 方法 | 路径 | 功能 | 请求体 | 响应 | 认证 |
|------|------|------|--------|------|------|
| POST | `/api/v1/entities/extract` | 从文本提取学术实体 | `{text, entity_types?}` | `{methods[], datasets[], metrics[], venues[], total_count}` | 是 |
| POST | `/api/v1/entities/{paper_id}/build` | 为论文构建知识图谱 | `{paper_text, authors?, references?}` | `{status, paper_id, message, entity_counts?}` | 是 |
| GET | `/api/v1/entities/{paper_id}/status` | 获取实体提取状态 | - | `{paper_id, has_entities, entity_counts, last_updated}` | 是 |

---

## 知识图谱查询 `/api/v1/graph`

| 方法 | 路径 | 功能 | 请求体 | 响应 | 认证 |
|------|------|------|--------|------|------|
| GET | `/api/v1/graph/nodes` | 获取图谱节点 | Query: `node_type?, limit, min_pagerank?, search?, offset?` | `{nodes: [{id, name, type, pagerank}], edges: [...]}` | 是 |
| GET | `/api/v1/graph/neighbors/{node_id}` | 获取节点邻居 | Query: `hops?, limit, relationship_type?` | `{nodes: [...], edges: [...]}` | 是 |
| GET | `/api/v1/graph/subgraph` | 获取子图 | Query: `paper_ids, depth?` | `{nodes: [...], edges: [...]}` | 是 |
| GET | `/api/v1/graph/pagerank` | 获取 PageRank Top N | Query: `limit, offset, recalculate?, min_year?, max_year?, domain?` | `{papers: [...], total}` | 是 |

---

## 论文对比 `/api/v1/compare`

| 方法 | 路径 | 功能 | 请求体 | 响应 | 认证 |
|------|------|------|--------|------|------|
| POST | `/api/v1/compare/compare` | 多论文对比分析 | `{paper_ids[], dimensions?, include_abstract?}` | `{paper_ids, dimensions, markdown_table, structured_data, summary}` | 是 |
| POST | `/api/v1/compare/evolution` | 方法演进时间线 | `{paper_ids[], method_name}` | `{method, paper_count, timeline: [{year, version, paper_id, paper_title, key_changes}], summary}` | 是 |

---

## RAG 问答 `/api/v1/queries`

| 方法 | 路径 | 功能 | 请求体 | 响应 | 认证 |
|------|------|------|--------|------|------|
| POST | `/api/v1/queries/query` | RAG 问答 (阻塞) | `{question, paper_ids?, query_type?, top_k?, conversation_id?}` | `{answer, query, sources[], confidence, conversation_id?, cached?}` | 是 |
| POST | `/api/v1/queries/stream` | RAG 问答 (SSE流) | `{question, paper_ids?, query_type?, top_k?, conversation_id?}` | `text/event-stream` | 是 |
| POST | `/api/v1/queries/session` | 创建对话会话 | `{paper_ids?}` | `{session_id, messages, paper_ids, created_at, message_count}` | 是 |
| GET | `/api/v1/queries/session/{session_id}` | 获取对话会话 | - | `{session_id, messages, paper_ids, created_at, message_count}` | 是 |
| DELETE | `/api/v1/queries/session/{session_id}` | 删除对话会话 | - | `204 No Content` | 是 |
| POST | `/api/v1/queries/agentic` | Agentic 搜索 (多轮) | `{query, query_type?, paper_ids?, max_rounds?, top_k?}` | `{answer, sub_questions[], sources[], rounds_executed, converged, metadata}` | 是 |

---

## 系统 `/api/v1/system`

| 方法 | 路径 | 功能 | 请求体 | 响应 | 认证 |
|------|------|------|--------|------|------|
| GET | `/api/v1/system/storage` | 获取存储使用情况 | - | `{vectorDB: {used, total, percentage}, fileStorage: {...}}` | 否 |
| GET | `/api/v1/system/logs/stream` | SSE 日志流 | - | `text/event-stream` | 是 |
| GET | `/api/v1/system/health` | 系统健康检查 | - | `{status, services: {postgres, redis, neo4j, milvus}, timestamp}` | 否 |

---

## Token 用量 `/api/v1/token-usage`

| 方法 | 路径 | 功能 | 请求体 | 响应 | 认证 |
|------|------|------|--------|------|------|
| GET | `/api/v1/token-usage/monthly` | 获取月度 Token 用量 | Query: `year?, month?` | `{total_tokens, input_tokens, output_tokens, total_cost_cny, request_count, daily_breakdown}` | 是 |

---

## PDF 解析 `/parse`

| 方法 | 路径 | 功能 | 请求体 | 响应 | 认证 |
|------|------|------|--------|------|------|
| POST | `/parse/pdf` | 解析 PDF 文件 | `file (PDF), arxiv_id?, force_ocr?` | `{status, filename, page_count, markdown, items, imrad, metadata}` | 是 |
| POST | `/parse/pdf/batch` | 批量解析 PDF | `files[] (PDF)` | `{status, task_id, file_count, message}` | 是 |
| GET | `/parse/pdf/status/{task_id}` | 查询解析任务状态 | - | `{task_id, status, message}` | 是 | ⚠️ Stub |

---

## 健康检查 `/health`

| 方法 | 路径 | 功能 | 响应 |
|------|------|------|------|
| GET | `/health/live` | Liveness probe (进程存活) | `{status: "alive", service: "scholarai-ai"}` |
| GET | `/health/ready` | Readiness probe (服务就绪) | `{status, service, ai_services: {...}}` |
| GET | `/health` | 完整健康检查 | `{status, service, models: {...}}` |

---

## 根路径 `/`

| 方法 | 路径 | 功能 | 响应 |
|------|------|------|------|
| GET | `/` | API 信息 | `{service, version, docs, redoc, health, status}` |

---

## 响应格式规范

### 成功响应
```json
{
  "success": true,
  "data": { ... }
}
```

### 错误响应 (RFC 7807 Problem Details)
```json
{
  "type": "https://scholarai.app/errors/validation",
  "title": "Validation Error",
  "status": 400,
  "detail": "具体的错误描述",
  "instance": "/api/v1/papers"
}
```

### 分页响应
```json
{
  "success": true,
  "data": {
    "items": [...],
    "total": 100,
    "limit": 20,
    "offset": 0
  }
}
```

---

## 认证说明

- **是**: 需要通过 JWT Token 认证 (Cookie 或 `Authorization: Bearer <token>`)
- **否**: 公开接口，无需认证

### Token 类型
- **Access Token**: JWT, 有效期 1 小时, 用于 API 认证
- **Refresh Token**: JWT, 有效期 7 天, 用于刷新 Access Token

---

## 通用查询参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `page` | 页码 (从1开始) | 1 |
| `limit` | 每页数量 (max 100) | 20 |
| `offset` | 偏移量 | 0 |
| `sortBy` | 排序字段 | `created_at` |
| `order` | 排序方向 (`asc`/`desc`) | `desc` |

---

## 状态码说明

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 204 | 删除成功 (No Content) |
| 400 | 请求参数错误 |
| 401 | 未认证 / Token 无效 |
| 403 | 无权限访问 |
| 404 | 资源不存在 |
| 409 | 资源冲突 (如重复) |
| 413 | 文件过大 |
| 429 | 请求过于频繁 (限流) |
| 500 | 服务器内部错误 |
| 504 | 超时 |
