---
phase: refactor-sprint
plan: Sprint3
subsystem: frontend
tags: [terminology, UI-consistency, interaction, error-handling]
requires: [Sprint1, Sprint2]
provides: [unified-terminology, ConfirmDialog, clean-console]
affects: [frontend/pages, frontend/components, frontend/hooks]
tech-stack:
  added: [ConfirmDialog.tsx, terminology.ts]
  patterns: [react-router-navigate, toast-error-feedback]
key-files:
  created:
    - frontend/src/config/terminology.ts
    - frontend/src/app/components/ConfirmDialog.tsx
    - frontend/docs/TERMINOLOGY.md
  modified:
    - frontend/src/app/pages/KnowledgeBaseDetail.tsx
    - frontend/src/app/pages/Login.tsx
    - frontend/src/app/pages/Dashboard.tsx
    - frontend/src/app/pages/Chat.tsx
    - frontend/src/app/pages/Settings.tsx
    - frontend/src/app/pages/Upload.tsx
    - frontend/src/app/hooks/useSessions.ts
    - frontend/src/hooks/usePapers.ts
    - frontend/src/services/sseService.ts
decisions:
  - D-C01-01: 术语规范表支持用户界面和内部工程术语分离
  - D-C03-01: ConfirmDialog 支持 default 和 danger 变体
  - D-C04-01: 保留生产环境 console.error，删除调试 console.log
metrics:
  duration: 45min
  completed_date: 2026-04-11
  tasks: 4
  files: 12
---

# Sprint 3: 统一前端设计系统与交互规则 Summary

**Commit:** 277e477

## One-liner

统一前端术语体系、创建 ConfirmDialog 替换原生 confirm、清理 window.location.href 和调试 console.log，实现无裸露工程术语、无原生阻断交互、无直接跳转的规范前端。

## 任务完成情况

| 任务 | 状态 | 描述 |
|------|------|------|
| C-01 | ✅ | 统一术语体系 - 创建 terminology.ts，清理 6 处裸露工程术语 |
| C-02 | ✅ | 页面气质统一 - 验证杂志风格已在 Phase 35 实现 |
| C-03 | ✅ | 原生阻断替换 - 创建 ConfirmDialog，替换 Chat/Settings 的 confirm |
| C-04 | ✅ | API错误收口 - Upload.tsx window.location.href → navigate，清理 7 处 console.log |

## 关键变更

### C-01: 术语统一

**创建术语规范表** (`terminology.ts`)
- 用户界面术语：62 个中文术语映射
- 内部工程术语：10 个技术术语（不直接展示）
- 提供查询函数 `getTerm()` 和 `getInternalTerm()`

**清理裸露工程术语**
| 文件 | 原术语 | 新术语 |
|------|--------|--------|
| KnowledgeBaseDetail.tsx:224 | Vector Search | 知识库检索 |
| KnowledgeBaseDetail.tsx:236 | Agentic Q&A | 问答 |
| KnowledgeBaseDetail.tsx:253 | Query vectorized chunks... | 输入您的问题... |
| KnowledgeBaseDetail.tsx:272 | Top N Segments Retrieved | 检索到 N 个相关片段 |
| KnowledgeBaseDetail.tsx:288 | Relevance: XX% | 相关度: XX% |
| Login.tsx:11,20 | Node 04 | 系统 |
| Dashboard.tsx:133 | API: Active | 服务正常 |
| Dashboard.tsx:134 | DB: Synced | 数据已同步 |

**输出文档** (`docs/TERMINOLOGY.md`)
- 术语对照表（用户术语 + 内部术语）
- 使用规则（5 条）
- Sprint 3 变更记录

### C-03: ConfirmDialog 创建

**组件设计**
- 支持 `default` 和 `danger` 变体
- 动画效果（motion scale + opacity）
- 橙色主题色（danger 使用红色）
- 按钮样式与整体系统一致

**替换场景**
| 文件 | 原交互 | 新交互 |
|------|--------|--------|
| Chat.tsx:111 | confirm() 删除会话 | ConfirmDialog danger 变体 |
| Settings.tsx:77 | confirm() 登出 | ConfirmDialog danger 变体 |

### C-04: 错误处理收口

**跳转方式**
- Upload.tsx:250: `window.location.href` → `navigate()`
- 导入 useNavigate hook

**console.log 清理**
| 文件 | 清理数量 |
|------|---------|
| useSessions.ts | 4 处 |
| sseService.ts | 3 处 |
| usePapers.ts | 1 处 |

**console.error 保留**
- 20 处错误处理 console.error 保留（生产环境错误追踪）

## 验收标准检查

| 标准 | 结果 |
|------|------|
| type-check 通过 | ✅ |
| 无裸露工程术语 | ✅ grep 未找到 Vector Search/Agentic Q&A/Node 04/API Active |
| 无原生 confirm | ✅ grep 未找到 confirm( |
| 无 window.location 直接跳转 | ✅ grep 未找到 window.location.href |
| 首页和应用内风格统一 | ✅ 杂志风格已在 Phase 35 实现 |

## 文件清单

**新增文件（3）**
- `frontend/src/config/terminology.ts` - 术语规范表
- `frontend/src/app/components/ConfirmDialog.tsx` - 统一确认弹层
- `frontend/docs/TERMINOLOGY.md` - 术语对照表文档

**修改文件（9）**
- `frontend/src/app/pages/KnowledgeBaseDetail.tsx` - 术语清理
- `frontend/src/app/pages/Login.tsx` - Node 04 → 系统
- `frontend/src/app/pages/Dashboard.tsx` - API/DB 状态术语
- `frontend/src/app/pages/Chat.tsx` - ConfirmDialog 替换
- `frontend/src/app/pages/Settings.tsx` - ConfirmDialog 替换
- `frontend/src/app/pages/Upload.tsx` - navigate 替换
- `frontend/src/app/hooks/useSessions.ts` - console.log 清理
- `frontend/src/hooks/usePapers.ts` - console.log 清理
- `frontend/src/services/sseService.ts` - console.log 清理

## Self-Check

✅ **PASSED**
- terminology.ts 存在
- ConfirmDialog.tsx 存在
- TERMINOLOGY.md 存在
- Commit 277e477 存在
- type-check 无错误

---

*Execution completed at 2026-04-11T15:10:00Z*