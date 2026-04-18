# ScholarAI 深度检查与改造建议报告（前端重点）

作者：glm5.1+37chengshan  
日期：2026-04-18

## 1. 执行摘要

本次检查覆盖：项目进度、前端缺陷与改造路径（重点）、后端 Python 意外退出根因、后端技术选型适配度。

核心结论：

1. 当前项目处于“功能可跑、架构过渡未收口”的阶段。
2. 前端已具备基础可用性（类型检查与测试通过），但存在明显的“迁移中双轨结构”与 UI/交互一致性问题，是下一阶段主攻点。
3. 后端在当前机器上的“Python 意外退出/不可用”首要根因不是业务代码，而是运行时环境不匹配：当前激活的是 system Python 3.14 且依赖严重缺失，与项目实际运行假设（Python 3.11 + 完整 requirements）不一致。
4. 技术选型总体可保留，但需要做环境分层与默认策略调整（开发环境轻量化、模型加载策略分级、向量栈收敛计划），否则持续出现“本地可运行性差、排障成本高”。

---

## 2. 检查范围与证据来源

检查方式：

1. 静态代码与配置审阅。
2. 前端命令验证（type-check、test:run）。
3. Python 环境与依赖实测。
4. 架构与契约文档一致性对照。
5. 已交付截图产物核对。

关键证据（节选）：

1. 页面截图清单：logs/screenshots/2026-04-18/manifest.json。
2. 前端路由与页面集合：apps/web/src/app/routes.tsx。
3. 前端大体量迁移组件：apps/web/src/features/chat/components/ChatLegacy.tsx。
4. 后端启动生命周期：apps/api/app/main.py。
5. 后端环境要求与启动方式：apps/api/README.md、apps/api/Dockerfile。
6. 运行时配置与模型路径：apps/api/app/config.py。
7. 本机 Python 环境实测：system Python 3.14.3，缺失 uvicorn/fastapi/torch/pymilvus/redis（现场命令验证）。

---

## 3. 项目进度评估（当前状态）

### 3.1 已完成项

1. 全部核心页面截图已产出并归档（13 张 + manifest）。
2. 前端类型检查通过（tsc --noEmit）。
3. 前端测试通过（33 files, 197 tests）。
4. 前后端主干架构均已落地，API 契约文档齐备。

### 3.2 未完成或过渡中项

1. 前端仍保留明显 legacy 过渡层（Chat、KB Detail 均有 LEGACY FREEZE 注释），新旧路径并存。
2. SSE 与聊天状态管理存在兼容层叠加（legacy event + new envelope 并行），长期维护成本高。
3. 后端本地运行链路对环境假设强，缺少“开箱即跑”的自检与降级保护。

### 3.3 阶段判断

当前不属于“可稳定演示并可扩展迭代”的成熟态，更接近：

1. 架构主线已形成。
2. 迁移与工程收口尚未完成。
3. 用户可见层（UI/交互质量）与开发者可用层（本地启动稳定性）是下一阶段两大短板。

---

## 4. 前端深度问题与改造路线（重点）

## 4.1 关键问题分级

### P0（优先级最高，直接影响迭代速度与稳定性）

1. Chat 模块过重且仍处于遗留过渡：
   - ChatLegacy 文件体量约 1365 行，且注释明确“迁移中，不应继续叠加业务逻辑”。
   - ChatWorkspace -> ChatRunContainer 最终仍直接挂载 ChatLegacy，说明新架构壳层已存在但核心尚未替换。

2. SSE 双轨兼容长期并存：
   - sseService/useChatStream/useSSE 并存。
   - 事件类型存在 legacy + 新协议双解析，测试日志中持续出现 message_id 缺失告警（虽可通过测试，但属于持续噪音和认知负担）。

### P1（高优先级，影响体验一致性与可维护性）

1. 页面层中等体量文件偏多（400-800 行区间文件集中），逻辑与视觉耦合偏高。
2. KnowledgeBaseDetail 仍处于 legacy 组件路线，状态管理与轮询逻辑沉积在页面内。
3. UI 组件生态偏杂（Radix + MUI + 自定义 + motion），视觉语言与交互规范尚未完全收敛。

### P2（中优先级，影响中长期质量）

1. tsconfig 里 baseUrl 已弃用，当前属于“可运行但未来升级有阻塞”的告警项。
2. 测试日志噪音较多（网络重试、预期异常打印、message_id contract 警告），会稀释真实失败信号。

## 4.2 前端改造目标（建议）

目标不是“继续修补 Legacy”，而是“完成迁移闭环并建立清晰边界”：

1. Chat：将 ChatLegacy 拆解为可组合的 domain hooks + render components，最终移除 legacy 主体。
2. KB Detail：把数据加载、轮询、导入状态机下沉到 features/kb/hooks/store，页面只保留编排与展示。
3. SSE：统一单一事件入口和单一状态机，legacy 协议兼容仅保留在 adapter 边界，禁止渗透到业务组件。
4. UI：建立页面级视觉和交互基线（排版、间距、状态反馈、加载态、错误态）并做一次统一收口。

## 4.3 分阶段实施计划（前端）

### Phase A（1 周）- 架构收口

1. 定义 Chat 新架构边界（container/presenter/store/effects）。
2. 新增 ChatV2 容器，按功能切片替换 ChatLegacy 的输入、流式消息、右侧面板。
3. 保留旧组件只做兼容，不再新增功能。

### Phase B（1-2 周）- 交互与视觉整治

1. 统一 loading/empty/error skeleton。
2. 统一对话区、引用区、推理区视觉层级。
3. 清理“测试可过但用户体验不稳定”的细节（重试提示、错误回退、状态跳变）。

### Phase C（1 周）- 噪音治理与质量门禁

1. 处理 tsconfig deprecation。
2. 压缩测试噪音日志（保留关键 contract violation，去除无价值输出）。
3. 建立 Chat/KB 页面级回归清单与截图基线对比。

---

## 5. 后端 Python 意外退出：根因分析

## 5.1 高置信根因（已实证）

1. 当前激活环境错误：
   - 实际环境为 system Python 3.14.3。
   - 后端依赖未安装（uvicorn、fastapi、torch、pymilvus、redis 均不可导入）。
   - 这会直接导致“服务起不来”或在启动链路早期异常退出。

2. 项目运行假设是 Python 3.11 体系：
   - README 明确 Python 3.11+。
   - Dockerfile 基线为 python:3.11-slim。
   - 仓库内存在 .venv（3.11）痕迹，说明项目实践也在 3.11 轨道。

结论：在当前机器上，最先要修复的是“解释器/依赖层面不一致”，而不是业务代码。

## 5.2 中置信风险（代码推断）

1. 启动即加载 AI 模型：
   - lifespan 启动阶段直接 load embedding + reranker。
   - 对本地显存/内存与底层库版本兼容要求高，启动成本大。

2. 模型与设备自动选择存在不确定性：
   - auto 设备选择会尝试 cuda/mps/cpu。
   - 在 macOS + MPS + 特定 torch/transformers 组合下，出现底层崩溃并非罕见。

3. 向量与模型栈复杂度高：
   - Milvus + Qwen/BGE + Celery/Redis + Neo4j 同时在本地协同，任一组件不匹配都可能引发连锁失败。

## 5.3 后端稳定性修复建议（按优先级）

### 立即执行（当天）

1. 固定解释器到 apps/api/.venv/bin/python（或新建 3.11 venv）。
2. 安装 requirements 并验证核心依赖导入。
3. 用最小启动参数先跑 health，再逐步开启模型加载。

### 短期执行（1 周）

1. 加启动前自检脚本：Python 版本、关键包、模型路径、Redis/Milvus 连接。
2. 将 embedding/reranker 改为可配置延迟加载（dev 默认 lazy，prod 可 eager）。
3. 对 MPS 路径加显式开关与告警（支持一键降级 CPU）。

### 中期执行（2-4 周）

1. 拆分运行配置 Profile：dev-lite、dev-full、prod。
2. 为模型初始化增加健康探针与超时保护，避免主进程被模型初始化拖死。

---

## 6. 后端技术选型评估与替换建议

## 6.1 结论总览

整体建议：

1. 主干框架保持不变（FastAPI + SQLAlchemy + Redis/Celery + Milvus + Neo4j）。
2. 重点不在“推翻重来”，而在“运行分层、默认策略、复杂度收敛”。

## 6.2 组件级评估矩阵

1. FastAPI：保留。理由：契约清晰、异步支持好、当前路由结构完整。
2. SQLAlchemy/Alembic：保留。理由：迁移与模型体系已经建立。
3. Celery + Redis：保留。理由：任务链路已落地；建议补齐可观测性和失败重试策略统一规范。
4. Milvus：短期保留，中期评估与 PGVector 的边界收敛。理由：当前检索与多模态逻辑已深绑定 Milvus，但本地部署复杂度较高。
5. Embedding 默认模型：建议分环境。
   - dev 默认 bge-m3（轻量、快速）
   - full/prod 可切 qwen3-vl（多模态）
6. Reranker：保留双实现，但统一策略层，避免文本/多模态混用时行为不可预期。

## 6.3 不建议立即替换的项

1. 不建议现在把 FastAPI 换框架。
2. 不建议立即把 Celery 全量替换为其它任务框架。
3. 不建议在前端未收口前同步做大规模后端重写。

---

## 7. 30/60 天落地里程碑

### 0-30 天

1. 前端：ChatLegacy 拆分一期 + KB Detail 状态下沉一期。
2. 后端：统一 Python 3.11 环境与依赖自检脚本落地。
3. 验证：前端关键路径截图回归 + 后端最小可用启动链路稳定运行。

### 31-60 天

1. 前端：SSE 单通道收口、legacy adapter 隔离。
2. 后端：模型加载策略 profile 化（dev-lite/dev-full/prod）。
3. 文档：同步更新 API 契约与资源模型，补齐实际运行指南。

---

## 8. 文档多维度审核（最终审查）

本报告按 5 个维度复核：

1. 准确性：
   - 结论与现场命令、代码位置、配置文件一致。
   - 区分了“已实证”与“代码推断”。

2. 完整性：
   - 覆盖项目进度、前端改造、后端崩溃根因、技术选型、里程碑。

3. 一致性：
   - 与 docs/architecture/system-overview.md、docs/architecture/api-contract.md 的边界描述不冲突。

4. 可执行性：
   - 提供了按优先级和时间窗的落地清单（当天、1 周、2-4 周、30/60 天）。

5. 风险可控性：
   - 指明先修环境与默认策略，再做结构重构，避免“大改动叠加大风险”。

审核结论：

1. 可作为当前阶段的执行基线文档。
2. 若后续发生接口形态变化或向量栈调整，需同步更新本报告与 API/资源模型文档。

---

## 9. 附：规划 vs 实现审计（最新发现）

### 概述

对比规划文档 `PR7_PR8_Chat稳定性_AgentNative_RAG升级实施方案.md`，发现项目存在 **"规划清晰，实现滞后"** 的问题：

- **Total Planned Phases:** 8 (Phase 6A ~ Phase 8C)
- **Fully Completed:** 1 (Phase 7A OCR 改动，part of Phase 6A壳化)
- **Partially Completed:** 5 (Phase 6A/6B/6C, 7A/7B, 8A)
- **Not Started / Reverted:** 7 (Phase 8B/8C, 7C 等大量改动)

### 关键发现

#### 🔴 "改了又消失" Pattern 1：分支中实现，主线部分合并

**例证：** Phase 7A (OCR 路由与 adaptive chunk size)
- ✅ feat/pr7-rag-parsing-stability 分支中已完整实现
- ✅ do_ocr=False 已 cherry-pick 到主线
- ❌ 但 adaptive_size 的完整逻辑、parse metadata 记录等仍在分支中未合并
- **结果：** 半成品落地，分支变成"孤立改动"

**建议：**
1. 检查 feat/pr7-rag-parsing-stability 与主线 HEAD 的 diff
2. 补齐所有缺失的 Phase 7A 改动（parse metadata、性能评测基线）
3. 考虑完整 merge 分支或明确标记"长期维护分支"

#### 🔴 "改了又消失" Pattern 2：后端完成，前端滞后

**例证：** Phase 6C (Agent-Native 确认闭环)
- ✅ 后端：agent_runner + chat_orchestrator 有 WAITING_CONFIRMATION 状态 + /confirm 端点
- ❌ 前端：confirmation_required UI 与 resume 执行缺失
- **结果：** 后端功能形同虚设

**建议：**
1. 补齐前端 confirmation panel UX
2. 建立 E2E 测试确保双端协调

#### 🔴 "改了又消失" Pattern 3：旧契约无限期并存

**例证：** Phase 8A (retrieval contract 统一)
- ✅ multimodal_search_service.py 已用新契约 (text, score, page_num)
- ❌ agentic_retrieval.py 仍有 fallback 逻辑：
  ```python
  score = chunk.get("score") or chunk.get("similarity") or (1 - distance)
  page_num = chunk.get("page_num") or chunk.get("page")
  ```
- **结果：** 两套字段并存，维护包袱永久化

**建议：**
1. 删除 fallback 逻辑或文档化失效期
2. 要求 source 端必须提供新字段，不允许 None
3. 加 contract validation gate（assertion）

### 未合并分支审视

| 分支 | 规划内容 | 为何未合并 | 建议 |
|------|---------|----------|------|
| feat/pr6-contracts-kb-chat | Chat/KB 协议 | 与 PR5 / PR20 冲突 | 评估是否可在 PR20 完成后重基 |
| feat/pr7-rag-parsing-stability | OCR 路由、chunking、metadata | 部分 cherry-pick，分支未完全收口 | 补齐遗漏 commit 后合并 |
| feat/pr8-rag-qa-contract-upgrade | retrieval contract、confidence | 包含破坏性改动，未通过评审 | 分解为小 PR 逐个 land |
| feat/pr8-ui-optimization | UI 性能 | 与 PR20 重叠 | 合并到 PR20 或标记为 superseded |
| feat/pr10-workspace-layering | workspace 分层 | 等待上游完成 | 重新评估依赖关系 |

### 修复优先级

#### 🔴 P0：本周完成（2 项）

1. **Phase 8A：清理 fallback 逻辑**
   - 删除 agentic_retrieval.py 中的 score/similarity/page fallback
   - 验证所有 source 都提供统一字段
   - 预计 20-30 行改动

2. **Phase 7A：验证 adaptive chunk size**
   - 补充 unit test 覆盖 section-specific size 优先级
   - 验证 born-digital PDF 实际性能（1-3s vs 10-30s 预期）
   - 预计 20-30 行测试

#### 🟠 P1：1 周内（2 项）

3. **Phase 6A：SSE 旧协议隔离**
   - 新增 sseAdapters.ts，映射 legacy event (thought/thinking_status) 到新协议
   - 隔离映射层，业务代码依赖新协议
   - 预计 100-150 行

4. **Phase 6A/6B：ChatLegacy 拆分规划**
   - 分析 ChatLegacy (1365 行)，按 domain 拆分：
     - ChatMessageList / CitationPanel / ToolTimeline / ReasoningPanel
   - 新增 ChatV2 容器，逐步替换旧路径
   - 禁止向 legacy 新增功能
   - 预计 2-3 天工作量

#### 🟡 P2：2 周内（2 项）

5. **Phase 7B：evidence metadata 框架**
   - 扩展 storage_manager 记录 content_subtype, section_path, anchor_text
   - 更新 Milvus schema / retrieval 接口
   - 预计 80-120 行

6. **Phase 8A：confidence 逻辑重算**
   - 替换 rag.py 的 "similarity.avg()" 为 "score coverage + diversity + support"
   - 补充 unit test
   - 预计 40-60 行

---

## 10. 附：建议立即执行的 8 条动作

1. 锁定 apps/api 解释器到 3.11 虚拟环境。
2. 执行后端依赖完整安装并做 import 自检。
3. 添加 backend preflight（版本/依赖/模型路径/基础连接）脚本。
4. 将 embedding/reranker 默认改为 dev lazy-load。
5. **【新增】执行 Phase 8A fallback 清理（P0）。**
6. **【新增】验证 Phase 7A adaptive chunk size（P0）。**
7. **【新增】启动 ChatLegacy 拆分规划（P1）。**
8. **【新增】梳理未合并分支，制定 re-base/supersede 决策（P1）。**

---

## 11. 完整审计报告

详见：[REVERTED_FEATURES_AUDIT.md](./REVERTED_FEATURES_AUDIT.md)
