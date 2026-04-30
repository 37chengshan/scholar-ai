---
owner: app-foundation
status: in-progress
depends_on: []
last_verified_at: 2026-04-21
evidence_commits: []
---

# 统一 runtime + 收口主链路 + 重构 Notes 执行计划

## 目标

在一个 PR 内完成三件事：

1. 明确并收口运行时与 Notes ownership 契约。
2. 将 Chat 固定为前端主执行入口，去掉页面层的多余桥接歧义。
3. 将 Notes 从“AI 笔记实体同步中心”改为“用户笔记 + 系统摘要展示”的知识落点层。

## 范围边界

本次不做：

- 数据库 schema 迁移。
- Search/KB 新功能扩展。
- 新增第二套 runtime。

本次必须完成：

- `paper.reading_notes` 只表示系统生成阅读摘要。
- `Note` 只表示用户可编辑笔记实体。
- Chat 页面固定走单一生产实现路径。
- Notes 侧不再把 `paper.readingNotes` 同步复制为真实 `Note`。
- 后端 notes API 与 worker 统一使用同一套 generated reading notes 写入语义。

## Wave 1：冻结 ownership 与契约

### 目标

- 冻结 `reading_notes` 与 `Note` 的 ownership。
- 提炼 Notes/Read 共用的 ownership helper。
- 固定 generated reading notes 的后端写入语义与响应形态。

### 目标文件

- `apps/web/src/features/notes/**`
- `apps/web/src/services/notesApi.ts`
- `apps/web/src/app/pages/Read.tsx`
- `apps/web/src/app/pages/Notes.tsx`
- `apps/api/app/api/notes.py`
- `apps/api/app/workers/notes_worker.py`
- `apps/api/app/services/reading_notes_service.py`

### 风险

- 历史 `__ai_note__` 数据仍可能存在，前端必须兼容但不能继续扩散。
- API 与 worker 若继续各写一套状态，会造成 `notes_version`、`is_notes_ready`、`notes_failed` 语义漂移。

### 验证

- `cd apps/web && npm run type-check`
- `cd apps/api && pytest -q tests/test_notes_worker.py --maxfail=1`

## Wave 2：收口 Chat 主链路

### 目标

- Chat 页面直接指向当前唯一生产实现。
- 旧容器保留兼容外壳，但不再承担主链路判断责任。

### 目标文件

- `apps/web/src/app/pages/Chat.tsx`
- `apps/web/src/app/pages/Chat.test.tsx`
- `apps/web/src/features/chat/components/ChatWorkspace.tsx`
- `apps/web/src/features/chat/components/ChatRunContainer.tsx`
- `apps/web/src/features/chat/workspace/ChatWorkspaceV2.tsx`

### 风险

- 入口改薄之后，任何 run/store 耦合问题都会直接暴露。

### 验证

- `cd apps/web && npx vitest run src/app/pages/Chat.test.tsx src/features/chat/hooks/useChatRuntimeBridge.test.ts src/features/chat/runtime/__tests__/chatRuntime.test.ts`

## Wave 3：Notes 展示层重构

### 目标

- Notes 左侧只列出用户可编辑笔记。
- 系统生成摘要作为 derived summary 展示，不再写入 `Note`。
- Read 页面只管理用户阅读笔记，不再承担 AI summary 投影职责。

### 目标文件

- `apps/web/src/app/pages/Notes.tsx`
- `apps/web/src/app/pages/Read.tsx`
- `apps/web/src/hooks/useNotes.ts`
- `apps/web/src/services/papersApi.ts`

### 风险

- 删除同步逻辑后，用户可能误以为 AI 内容丢失，因此必须在 Notes UI 中保留可见的系统摘要入口。

### 验证

- `cd apps/web && npm run type-check`
- `cd apps/web && npx vitest run src/app/pages/Chat.test.tsx`

## 文档同步

本次 PR 至少同步：

- `docs/specs/architecture/api-contract.md`
- `docs/specs/architecture/system-overview.md`
- `docs/specs/domain/resources.md`

同步要点：

- 明确 `paper.reading_notes` 是系统生成摘要，不是用户笔记实体。
- 明确 `Note` 是用户知识沉淀对象。
- 明确 Chat 为当前前端主执行链路入口。

## 完成定义

- Notes 页面不再创建或更新 AI note 实体。
- Read 页面只绑定用户可编辑阅读笔记。
- `generate/regenerate/worker` 对 reading notes 的写入状态一致。
- Chat 页面入口只保留单一路径。
- 文档与实现一致，最小验证通过。