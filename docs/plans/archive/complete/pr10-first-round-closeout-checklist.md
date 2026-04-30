# PR10 第一轮收尾清单（Round 1）

## 1. 目标与范围

本清单用于 PR10 的第一轮收尾，聚焦两项：

1. ChatLegacy / KnowledgeBaseDetailLegacy 下线前置条件
2. hooks 职责收口（app/hooks 与 features/hooks）

不在本轮范围内：

- 全量 UI 重构
- 后端检索算法改造
- 观测平台完整接入

## 2. Legacy 下线条件

### 2.1 ChatLegacy 下线条件

- [ ] 条件 C1：`apps/web/src/features/chat/components/ChatWorkspace.tsx` 不再直接渲染 `ChatLegacy`
- [ ] 条件 C2：会话生命周期（创建、切换、删除、停止）由 workspace 层 hook 驱动
- [ ] 条件 C3：SSE 流状态与消息回填不依赖 `ChatLegacy` 内部本地状态
- [ ] 条件 C4：关键行为回归测试通过（发送消息、停止、会话切换、citation 展示）
- [ ] 条件 C5：`ChatLegacy` 仅保留兼容壳（可选），并标注退役日期

### 2.2 KnowledgeBaseDetailLegacy 下线条件

- [x] 条件 K1：`KnowledgeBaseWorkspace` 不再直接渲染 `KnowledgeBaseDetailLegacy`
- [x] 条件 K2：导入任务轮询由 `features/kb/hooks` 统一承接
- [ ] 条件 K3：papers/import-jobs/search 的状态源从页面组件迁出并集中到 workspace 层
- [ ] 条件 K4：关键行为回归测试通过（导入、轮询刷新、搜索、跳转 quick-chat/read）
- [ ] 条件 K5：`KnowledgeBaseDetailLegacy` 降级为兼容壳或删除

## 3. hooks 职责矩阵（第一轮收口）

| 领域 | 应放置位置 | 第一轮约束 | 禁止项 |
| --- | --- | --- | --- |
| 页面路由装配 | `apps/web/src/app/pages` | 只做 route-level 组装，不承载业务状态 | 在 page 中直接实现业务流程 |
| 通用跨域 hooks | `apps/web/src/app/hooks` | 仅保留跨 feature、无业务耦合能力 | 在 app/hooks 写 chat/kb/search 业务逻辑 |
| Chat 业务 hooks | `apps/web/src/features/chat/hooks` | 承接 session/stream/scope/message 业务编排 | 将 chat 业务回流到 app/hooks |
| KB 业务 hooks | `apps/web/src/features/kb/hooks` | 承接 import/polling/search/workspace 状态 | 在页面组件内直写 workflow |
| Search 业务 hooks | `apps/web/src/features/search/hooks` | 承接 unified search/author search/import flow | 继续依赖旧 `src/hooks/useSearch.ts` 承担全部职责 |

第一轮归并动作：

- [x] H1：盘点 `apps/web/src/app/hooks` 中与 chat/kb/search 强耦合的 hooks
- [ ] H2：迁移 H1 识别出的业务 hooks 至各自 `features/*/hooks`
- [ ] H3：在 page 层仅保留组合与参数传递，不保留业务流程分支
- [x] H4：为迁移 hooks 补齐最小单测或集成测试

## 4. 第一轮可执行项（Round 1 Execution Items）

- [x] R1：建立 ChatLegacy 功能映射表（legacy 逻辑 -> workspace hook 目标归属）
- [x] R2：建立 KB Legacy 功能映射表（legacy 逻辑 -> workspace hook 目标归属）
- [x] R3：标注并冻结 legacy 文件新增逻辑入口（仅允许修 bug，不允许加新流程）
- [x] R4：完成 app/hooks 与 features/hooks 的冲突清单
- [ ] R5：提交第一轮迁移 PR（只迁移职责，不混入样式重构）

## 4.1 Round 1 审查产物（本轮新增）

### ChatLegacy 功能映射（R1）

| Legacy 责任 | 当前位置 | 目标归属 | Round 1 状态 |
| --- | --- | --- | --- |
| 会话生命周期（create/switch/delete） | `features/chat/components/ChatLegacy.tsx` + `app/hooks/useSessions.ts` | `features/chat/hooks/useChatSession.ts` + workspace store | in-progress |
| 流式状态机与 SSE 事件绑定 | `features/chat/components/ChatLegacy.tsx` + `app/hooks/useChatStream.ts` | `features/chat/hooks/useChatStreaming.ts` + workspace orchestration | in-progress |
| UI 输入/面板/删除确认本地状态 | `features/chat/components/ChatLegacy.tsx` | `features/chat/components/*` + feature store | in-progress |

### KB Legacy 功能映射（R2）

| Legacy 责任 | 当前位置 | 目标归属 | Round 1 状态 |
| --- | --- | --- | --- |
| Import 轮询 | `features/kb/components/KnowledgeBaseDetailLegacy.tsx` | `features/kb/hooks/useImportJobsPolling.ts` | done |
| KB Workspace 查询与状态整合 | `features/kb/components/KnowledgeBaseDetailLegacy.tsx` | `features/kb/hooks/useKnowledgeBaseWorkspace.ts` | in-progress |
| 页面 Tab + 路由同步 | legacy page/component | `features/kb` workspace shell + route 层装配 | in-progress |

### hooks 冲突清单（R4）

| 冲突点 | 现状 | 收口方向 |
| --- | --- | --- |
| chat session/stream 仍依赖 `app/hooks` | `features/chat/hooks/useChatSession.ts` -> `app/hooks/useSessions.ts`；`useChatStreaming.ts` -> `app/hooks/useChatStream.ts` | 将业务编排迁入 `features/chat/hooks`，`app/hooks` 仅保留跨域基础能力 |
| search 仍依赖旧通用 hook | `features/search/hooks/useUnifiedSearch.ts` -> `src/hooks/useSearch.ts` | 逐步迁入 `features/search/hooks` 并保持 URL/state contract |
| legacy 组件仍承载业务流程 | `ChatLegacy` 和 `KnowledgeBaseDetailLegacy` 仍存在业务状态与 side effects | 仅保留兼容壳，新逻辑冻结在 workspace/hook 层 |

## 5. 验收与验证命令

前端验证：

- `cd apps/web && npm run type-check`
- `cd apps/web && npm run test -- --runInBand`（若项目脚本支持）

治理验证：

- `bash scripts/check-doc-governance.sh`
- `bash scripts/check-governance.sh`

结果记录：

- [x] 验证结果写入本文件末尾的“执行记录”
- [x] 失败项必须记录“复现命令 + 修复提交 + 复测结果”

## 6. 执行记录（Round 1）

- 日期：2026-04-17
- 执行人：Copilot (GPT-5.3-Codex)
- 变更摘要：
	- 完成 legacy 下线条件与 hooks 职责边界盘点
	- 建立 ChatLegacy/KB Legacy 映射表与 hooks 冲突清单
	- 对 R1/R2/R3/R4 给出可追踪状态
- 验证摘要：
	- 证据检索：`cd apps/web && rg -n "ChatLegacy|KnowledgeBaseDetailLegacy|useImportJobsPolling|useChatStream|useSessions|useSearch" src`
	- 计划治理：`bash scripts/check-plan-governance.sh`
	- 总治理：`bash scripts/check-governance.sh`
- 未完成项与阻塞：
	- C1/C2/C3/C4/C5 尚未完成，`ChatRunContainer` 仍渲染 `ChatLegacy`
	- K3/K4/K5 尚未完成，legacy 页面仍保留状态与 workflow
	- H2/H3/R5 待后续职责迁移 PR 落地
- 下一轮入口条件：
	- 先完成 `ChatLegacy` 功能拆解（session + stream + message）到 `features/chat/hooks`
	- 再执行 KB legacy 状态迁移与删除/兼容壳策略

### Round 1 严格复核补录（2026-04-17）

- 复现命令：
	- `cd apps/web && pnpm vitest run src/services/chatApi.test.ts src/features/kb/components/KnowledgeWorkspaceShell.test.tsx src/app/pages/Chat.test.tsx`
	- `cd apps/web && pnpm type-check`
	- `bash scripts/check-plan-governance.sh`
	- `bash scripts/check-governance.sh`
- 结果：
	- 前端：3 files, 5 tests passed
	- TypeScript：type-check passed
	- 治理门禁：全部通过
- 失败项记录：
	- 本轮范围内无失败。
	- 发现历史基线漂移：`apps/api/tests/test_rag.py`（旧路由断言）与 `apps/api/tests/unit/test_agentic_citations.py`（旧私有方法断言），已在 `REVIEW.md` 记录并标注为后续基线清理项。
