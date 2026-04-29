# v3.0FR Refactor Scope Matrix

## In Scope

1. `apps/web/src/features/chat/components/ChatLegacy.tsx`
2. `apps/web/src/features/kb/components/KnowledgeBaseDetailLegacy.tsx`
3. `apps/web/src/features/kb/components/KnowledgePapersPanel.tsx`
4. `apps/web/src/app/pages/Read.tsx`
5. `apps/web/src/app/pages/Notes.tsx`
6. 与以上页面直接相关的新 store 文件

## Out Of Scope

1. `ChatWorkspaceV2` 深层职责重组
2. `KnowledgeWorkspaceShell` 标签结构重排
3. `Compare / Review` 页面视觉和 IA 重构
4. 全站 Button-Navigation 语义整改
5. 全组件 canonical registry 全量清洗

## Expected Artifacts

1. 删除 2 个 legacy bridge 文件
2. 1 个 KB list virtualization 实现
3. 2 个 preference store
4. focused validation 结果