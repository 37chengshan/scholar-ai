# Page Audit for Workflow Reset

作者：glm5.1+37chengshan
日期：2026-04-20

| route | current purpose | decision | replacement | blockers | owner |
| --- | --- | --- | --- | --- | --- |
| / | Landing/营销页 | keep (rewrite) | Agent-Native landing | 无 | FE |
| /chat | 对话与问答 | keep | Chat/Workspace 主入口 | 无 | FE |
| /knowledge-bases | 知识库列表 | keep (rename in nav) | Library 主入口 | 历史命名保留兼容 | FE |
| /knowledge-bases/:id | 知识库详情/导入/检索/问答入口 | keep | Library 上下文工作台 | 无 | FE |
| /search | 外部检索与导入 | keep | Search（接入 workflow shell） | 无 | FE |
| /read/:id | 阅读器与上下文操作 | keep | Read（接入 workflow shell） | 无 | FE |
| /settings | 用户设置 | keep | Settings（工具页） | 无 | FE |
| /dashboard | 传统 KPI 仪表盘 | downgrade | route redirect -> /knowledge-bases；不在一级导航显示 | 旧链接兼容 | FE |
| /notes | 独立笔记页面 | downgrade | 从一级导航移除；作为 Read/Library 上下文能力入口 | 用户习惯迁移提示 | FE |
| /login,/register,/forgot-password,/reset-password | 认证流程 | keep | 认证工具流程 | 无 | FE |

## 审计结论

1. 一级导航收敛为 Chat / Library / Search / Settings。
2. Dashboard 不再作为主入口，保留兼容重定向。
3. Notes 不再作为主入口，保留路由但以“上下文笔记能力”定位。
4. 核心 workflow 页面统一挂载 Workflow Shell。
