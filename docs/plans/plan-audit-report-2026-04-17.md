# ScholarAI 计划完成度审查报告（2026-04-17）

## 1. 审查目的与范围

本报告回答两个问题：

1. 为什么 docs/plans 下很多计划显示“未完成/部分完成”。
2. 具体缺什么、下一步如何完成。

审查范围：

- docs/plans 下主计划文档（PR3/4/5/6/7/8/10/11/12）。
- 代码现状对照（apps、packages、近期提交记录）。

---

## 2. 审查方法与关键证据

### 2.1 文档侧证据

- PR7/8 文档末尾交付清单大量未勾选（Chat 稳定性、解析升级、问答升级均为待办）。
- PR10 文档定义了 Phase 0~3 的完整路线，但文档本身没有“执行回填区”，难以判定每个 phase 的真实完成状态。
- PR5 与 PR6 文档存在内容重叠与编号漂移：
  - 两份文档主题相同（共享契约 + 工作台可用性），但标题编号不一致。
  - 文档内部对“PR-5/PR-6”命名存在交叉。

### 2.2 代码侧证据

已落地（与旧计划假设不一致）：

- apps/api/app/schemas 已存在。
- apps/api/app/repositories 已存在。
- packages/types 与 packages/sdk 已存在真实 src 与 dist，不再是纯 README 占位。
- PR10 相关 workspace 文件已存在：ChatWorkspace、KnowledgeBaseWorkspace、SearchWorkspace、chatWorkspaceStore、kbWorkspaceStore。

仍存在的技术债证据：

- Chat 旧实现仍然偏重：ChatLegacy.tsx 体量大（>1300 行级别）。
- app/hooks 与 features/hooks 并行存在（如 useChatStream / useSessions 仍在 app/hooks 中），说明状态真源收口未完全完成。

### 2.3 交付节奏证据（近期提交）

- PR10、PR11、PR12 相关提交已落地（#10/#11/#12/#14/#15 等）。
- 说明“不是没有做”，而是“计划文档与执行回写不同步”。

---

## 3. 逐计划审查结论（缺什么）

| 计划 | 审查结论 | 主要缺口 |
|---|---|---|
| PR3 物理迁移到 apps | 基本完成 | 缺少“最终状态封版记录”（已完成证据分散在脚本/提交中） |
| PR4 迁移后稳定化 | 基本完成 | 缺少将验收结果回填到计划文档的固定模板 |
| PR5 共享契约收口与前端工作台 | 部分完成 | 后端契约全域对齐、前端多状态源收口、文档回填不足 |
| PR6 同主题计划 / 执行优化 | 部分完成 | 与 PR5 存在编号与范围重叠，执行口径不唯一 |
| PR7/PR8 Chat稳定性 + RAG 升级 | 明显未完成 | 文档定义了完整任务，但缺少按 slice 推进和验收回填，末尾清单大量未勾选 |
| PR10 workspace 分层稳定化 | 部分完成 | workspace 骨架已落地，但 legacy 体量与状态真源收口仍未收尾 |
| PR11 Harness Observability | 已完成 | 需做“完成后维护责任”定义（谁跟进告警/指标演进） |
| PR12 Benchmark 基线评测 | 已完成 | 需把阈值维护流程纳入常规发布节奏 |

---

## 4. 根因分析（为什么会“看起来没完成”）

### 根因 1：计划文档类型混用（蓝图 vs 执行台账）

当前很多文档是“设计说明书”，不是“可回填执行台账”。
结果是：代码做了，文档状态不变，看起来一直“未完成”。

### 根因 2：编号与范围漂移（PR5/PR6）

同主题出现多份计划，且编号/标题有交叉，导致团队不知道应以哪份为真源。

### 根因 3：依赖链过长、阶段粒度偏大

例如 PR7/8 把 Chat 稳定、解析升级、问答升级串成长链路，任一前置未闭环就会卡住后续阶段。

### 根因 4：计划假设滞后于代码现实

部分计划仍描述“schemas/repositories 不存在”“packages 仅占位”，而代码已经演进，导致计划与现实错位。

### 根因 5：缺少“合并即回写”的流程门禁

目前 CI 主要验证代码质量与治理脚本，但没有强制“计划状态同步更新”。

---

## 5. 如何做（可执行补完方案）

## 5.1 先修计划系统（1个轻量治理 PR）

目标：先把“计划真源”收敛，避免继续边做边乱。

动作：

1. 建立单一总览文件：docs/plans/PLAN_STATUS.md（唯一状态面板）。
2. 给每个计划增加统一头部元数据：
   - owner
   - status（not-started/in-progress/done/blocked）
   - depends_on
   - last_verified_at
   - evidence_commits
3. 明确 PR5/PR6 去重规则：
   - 保留一份主计划（建议保留 PR5 或重命名为统一编号）。
   - 另一份标记 superseded，并指向主计划。
4. 新增门禁脚本（可后续接入 CI）：
   - 检查每个 active 计划是否有 last_verified_at 与 evidence_commits。

验收：

- docs/plans 下只有一份 active 的“共享契约 + 工作台”主计划。
- 所有 active 计划可在 2 分钟内从总览看出状态与证据。

## 5.2 PR7（解析升级）拆成可落地 3 个切片

切片 P7-A：解析契约与路由收口

- 固化 OCR 路由开关与 born-digital 默认策略。
- 修复 adaptive chunking 的统一覆盖问题。

切片 P7-B：证据索引增强

- 标准化证据 metadata（section/page/source/span）。
- 强化图表-正文关联字段。

切片 P7-C：质量门禁

- 增加 parse regression fixtures。
- 建立最小质量阈值（召回/分块质量/错误率）。

验收命令（建议基线）：

- cd apps/api && pytest -q tests/unit --maxfail=1
- cd apps/api && pytest -q tests/integration --maxfail=1
- bash scripts/check-governance.sh

## 5.3 PR8（问答升级）拆成可落地 3 个切片

切片 P8-A：retrieval contract 统一

- 统一 score/similarity、page/page_num、content/text 映射。
- 修复 confidence 计算口径。

切片 P8-B：混合检索 + 结构化重排

- 引入 hybrid retrieval（向量 + 关键词/过滤）
- rerank 输出统一证据结构。

切片 P8-C：claim-level synthesis + citation verifier

- 回答按 claim 组织。
- 每条 claim 都有 citation 证据与可验证性标记。

验收命令（建议基线）：

- cd apps/api && pytest -q tests/evals --maxfail=1
- python scripts/eval_retrieval.py
- python scripts/eval_answer.py

## 5.4 PR10 收尾（稳定化）

重点不是再建新壳，而是去 legacy 和收口状态真源：

1. 定义 ChatLegacy/KBLegacy 下线条件（按模块、按里程碑）。
2. 收敛 app/hooks 与 features/hooks 的重复职责。
3. 将 workspace store 从“薄壳”升级为“业务状态承载层”，并删掉重复状态源。
4. 对 chat/kb/search 分别补齐回归测试。

---

## 6. 建议执行顺序（未来两周）

Week 1：

1. 先做“计划系统修复 PR”（5.1）。
2. 启动 PR7 切片 P7-A（解析契约与 adaptive chunking）。
3. 同步建立 PR7 的验收回填模板。

Week 2：

1. 推进 PR7 的 P7-B/P7-C。
2. 并行启动 PR8 的 P8-A。
3. 对 PR10 做收尾清单第一轮（legacy 下线条件 + hooks 职责收口）。

---

## 7. 结论

当前“很多计划没完成”的本质不是单一研发效率问题，而是：

- 计划系统缺少单一真源与回填机制；
- 部分计划编号/范围重叠；
- 依赖链过长导致执行被卡；
- 文档假设没有跟代码现实同步。

建议先用一个小治理 PR 修复“计划管理层”，再按 PR7/PR8/PR10 的小切片推进。
这样可以把“看起来一直没完成”的状态，转成每周可验证、可关闭的交付节奏。
