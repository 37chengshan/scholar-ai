# ScholarAI 前端术语规范

## 面向用户的术语（中文）

| 英文键 | 中文术语 | 使用场景 |
|--------|---------|---------|
| paper | 论文 | 论文标题、论文列表 |
| papers | 论文库 | 导航菜单、页面标题 |
| knowledge-base | 知识库 | 知识库名称、详情页 |
| knowledge-bases | 知识库列表 | 导航菜单、页面标题 |
| kb-retrieval | 知识库检索 | 知识库检索标签 |
| kb-qa | 问答 | 知识库问答标签 |
| upload | 上传 | 上传入口、上传历史 |
| search | 搜索 | 搜索入口、搜索结果 |
| read | 阅读 | 阅读入口、阅读进度 |
| chat | 对话 | 对话历史、对话页 |
| notes | 笔记 | 笔记列表、笔记编辑 |
| annotations | 批注 | 批注列表、添加批注 |
| session | 对话 | 对话会话 |
| sessions | 对话历史 | 对话历史列表 |
| query | 问答 | 知识库问答 |
| query-result | 问答结果 | 问答结果展示 |
| citation | 引用 | 引用来源、引用跳转 |
| citations | 引用来源 | 引用列表 |
| snippet | 片段 | 论文片段、引用片段 |
| abstract | 摘要 | 论文摘要 |
| authors | 作者 | 作者列表、作者信息 |
| keywords | 关键词 | 论文关键词 |
| tags | 标签 | 知识库标签、笔记标签 |
| progress | 阅读进度 | 阅读进度保存 |
| import | 导入 | 导入论文、导入知识库 |
| export | 导出 | 导出论文、导出知识库 |
| batch-delete | 批量删除 | 批量操作 |
| batch-export | 批量导出 | 批量操作 |
| storage | 存储空间 | 存储使用量 |
| dashboard | 仪表盘 | 仪表盘页面 |
| settings | 设置 | 设置页面 |
| profile | 个人资料 | 用户资料 |

## 内部工程术语（不在用户 UI 直接展示）

| 英文键 | 中文术语 | 说明 |
|--------|---------|-----|
| vector-search | 向量检索 | 技术说明中可使用 |
| embedding | 文文嵌入 | 技术说明中可使用 |
| rag | RAG | 技术文档中使用 |
| llm | LLM | 技术文档中使用 |
| semantic-scholar | Semantic Scholar API | 外部服务，保持英文 |
| pdf-parse | PDF 解析 | 技术说明 |
| chunk | 文本块 | 技术说明 |
| node | 节点 | 内部系统状态 |
| api-status | API 状态 | 内部系统状态 |
| db-status | 数据库状态 | 内部系统状态 |

## 术语使用规则

1. **面向用户的功能名称使用中文**
   - 导航菜单、页面标题、按钮文本、卡片标题都使用中文术语

2. **技术细节可用工程术语，但需用中文解释**
   - 例如："知识库检索（基于向量检索技术）"

3. **外部服务名称保持英文**
   - 例如：Semantic Scholar、OpenAI API

4. **同一对象使用统一术语**
   - 不允许在不同页面使用不同称呼
   - 例如：知识库不能同时叫"知识库"和"文库"

5. **禁止裸露工程术语**
   - 不允许直接展示 "Vector Search"、"Agentic Q&A" 等
   - 必须翻译为中文或用中文说明

## 实施变更

### Sprint 3 变更记录

| 文件 | 变更内容 |
|------|---------|
| KnowledgeBaseDetail.tsx | "Vector Search" → "知识库检索" |
| KnowledgeBaseDetail.tsx | "Agentic Q&A" → "问答" |
| KnowledgeBaseDetail.tsx | "Query vectorized chunks..." → "输入您的问题..." |
| KnowledgeBaseDetail.tsx | "Top N Segments Retrieved" → "检索到 N 个相关片段" |
| KnowledgeBaseDetail.tsx | "Relevance: XX%" → "相关度: XX%" |
| Login.tsx | "Node 04" → "系统" |
| Dashboard.tsx | "API: Active" → "服务正常" |
| Dashboard.tsx | "DB: Synced" → "数据已同步" |
| Upload.tsx | window.location.href → navigate() |
| Chat.tsx | confirm() → ConfirmDialog |
| Settings.tsx | confirm() → ConfirmDialog |

---

*Last updated: 2026-04-11 (Sprint 3)*