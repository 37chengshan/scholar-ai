# Workflow UI / IA Reset

作者：glm5.1+37chengshan
日期：2026-04-20

## 新信息架构

### 一级导航
1. Chat / Workspace
2. Library
3. Search
4. Settings（主导航右侧工具入口）

### 上下文导航（由 Workflow Shell 提供）
1. Current Scope
2. Active Run / Job
3. Pending Actions
4. Recoverable Tasks
5. Artifacts / Evidence
6. Recent Activity

## 路由策略

1. `/chat` 保留为 Workspace 主入口。
2. `/knowledge-bases` 保留并在导航命名为 Library。
3. `/dashboard` 不再暴露一级入口，路由重定向到 `/knowledge-bases`。
4. `/notes` 不再暴露一级入口，作为上下文能力保留。

## 统一 UI 语义

1. 状态：`idle / running / waiting / failed / completed / cancelled`
2. 动作：`continue / retry / resolve / open / jump`
3. 作用域：`global / knowledge-base / paper / run`
4. 产物：`answer / citation / note / import-report / session`
5. 待处理：`pending action / recoverable task`

## 文案规范

1. 避免“跳页完成任务”叙事，改为“在工作流中推进任务”。
2. 空状态统一强调：当前阶段、下一步动作、可恢复入口。
3. 证据与引用统一使用 `Evidence / Artifacts` 术语。

## 迁移说明

1. Dashboard：保留兼容但不再作为产品主线。
2. Notes：从导航移除，改由 Read/Library 上下文进入。
3. 旧页面能力优先合并到 workflow shell 与上下文面板。
