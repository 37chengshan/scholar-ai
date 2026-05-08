---
owner: product-engineering
status: not-started
depends_on:
  - 06_v3_0_overview_plan
  - 2026-04-29_v3_0_closeout_checklist
last_verified_at: 2026-05-02
evidence_commits:
  - wip-v4-0-kickoff
---

# 18 v4.0 纵览计划：Productized Research Workflow + Beta Release

> 日期：2026-05-02  
> 状态：draft / direction-confirmed-ac-priority  
> 用途：定义 ScholarAI v4.0 大版本主线、Phase 拆分与启动边界。  
> 说明：用户已确认 v4.0 采用 A+C 优先：产品化研究工作流 + Beta release / 稳定性；同时增加两个独立前端精细打磨 phase；B 类学术 RAG 技术升级保留为一个技术优化 phase 和一个测试评测 phase。

## 0. 草案状态

本文件已按用户确认的 A+C 优先方向收敛，但仍保留为 phase-level 草案。后续处理规则：

1. A：产品化研究工作流是 v4.0 主产品主线。
2. C：Beta release、稳定性、演示资产是 v4.0 交付主线。
3. 前端非常细致打磨拆成两个独立 phase，而不是附属在产品主线里。
4. B：学术 RAG 技术升级不作为开场主线，只保留一个优化 phase 和一个测试评测 phase。
5. 具体每个 phase 仍需单独研究文档和执行计划后再进入实现。

## 1. v4.0 定位

v4.0 的目标不是重写 ScholarAI，也不是一开始押注新 RAG 框架。v4.0 要先把 v3.0 已经形成的 Search、Import、KB、Read、Chat、Notes、Compare、Review、Truth + Route 和 comparative gate，收敛成一个可连续使用、可演示、可恢复、可反馈的研究工作流产品。

统一表达为：

```txt
ScholarAI v4.0 =
Productized Research Workflow
+ Beta-ready Research Workspace
+ Reliable Full-chain Execution
+ Citation-backed Review Artifacts
+ Frontend Experience Craft
+ Frontend Interaction Quality
+ Targeted Academic RAG Optimization
+ Evidence-based Release Testing
```

v4.0 的产品目标是：用户能围绕一个研究目标稳定完成搜索、入库、阅读、问答、笔记、对比、综述和导出，并能理解当前状态、失败原因、下一步动作和证据质量。技术升级服务这个产品目标，而不是反过来让产品流程迁就技术实验。

## 2. 启动前提

本计划基于当前仓库真实状态：

1. v3.0 已有 meaningful code，但仍不能按“完全收口”处理。
2. `docs/plans/v3_0/active/overview/2026-04-29_v3_0_closeout_checklist.md` 仍记录 Phase D/F/G 等验证和发布材料缺口。
3. 2026-05-01 后端审查记录了 Task smoke、Chat persistence、Session replay 等风险；其中 `TaskService.retry_task` smoke 已在 2026-05-02 复测通过。
4. Phase H/I/J 已经提供 runtime truth、Truth + Route、comparative gate 的第一批基础，但 v4.0 只把它们作为产品化 workflow 和测试门禁的支撑，不把 B 类技术升级作为开场主线。
5. 前端方向已明确为 Chat 为中心、Dashboard 只做指挥台、跨页 handoff 预填待发送、阻塞优先。

因此 v4.0 的第一步必须是 Phase 0 收口，而不是直接新开大功能。

## 3. v4.0 规划原则

1. 不新增根级 doc、tmp、legacy、平行前端或平行后端目录。
2. 新代码仍只落在 `apps/web`、`apps/api` 和既有 `packages` 边界内。
3. Dashboard 继续作为指挥台，不承载具体功能执行。
4. Chat 继续作为执行核心，Search / KB / Read / Notes / Compare / Review 负责准备输入、展示状态和深链跳转。
5. Agentic / Graph / global synthesis 能力只允许作为后续优化 phase 接入现有 workflow，不允许另建第二套 agent runtime。
6. Claim / citation / evidence 是 v4.0 的共同内核，不再为不同页面维护不同口径。
7. 所有长任务必须有可恢复状态、用户可见进度、失败原因、重试入口和 run artifact。
8. 所有 benchmark / release 结论必须有 baseline / candidate / diff / verdict，不接受口头放行。

## 4. v4.0 Phase 总览

## Phase 4.0-0：Version Gate and v3.0 Residual Close-out

### 核心思路

先把 v3.0 的残留验证、后端 smoke、前端测试、full-chain walkthrough、Beta 资产和文档状态收口到 v4.0 可启动基线。

### 结果形态

1. v3.0 未完成项被明确分类为 `closed / carried-forward / rejected`。
2. 后端最小 smoke、Chat persistence、Session replay、Phase H/J 目标测试有复测结果。
3. 前端 type-check 与核心 test runner 风险有复测结果。
4. Search -> Import -> KB -> Read -> Chat -> Notes -> Compare -> Review 至少有一条 full-chain evidence。
5. v4.0 目录、PLAN_STATUS、Phase ledger、docs 入口全部同步。

### 本阶段边界

只做启动收口和风险归档，不新增 agentic workflow 功能。

## Phase 4.0-1：Productized Research Workflow

### 核心思路

把现有 Search -> Import -> KB -> Read -> Chat -> Notes -> Compare -> Review 从“页面集合”升级为连续研究工作流。用户不需要理解内部模块边界，只需要看到当前研究目标、已完成步骤、阻塞项、下一步动作和可恢复入口。

### 结果形态

1. Dashboard 展示研究目标、阻塞项和下一步，不执行具体动作。
2. Search / KB / Read / Chat / Notes / Compare / Review 共享一个 workflow context。
3. Chat 接收跨页 handoff，预填待发送，不自动执行。
4. 失败、空状态、导入中、索引中、证据不足等状态在各页口径一致。

### 本阶段边界

不重做信息架构，不新增并行工作台；只把现有主链挂上稳定 workflow 状态。

## Phase 4.0-2：Beta Release Hardening

### 核心思路

把 v3.0 已有能力包装成可演示、可试用、可反馈的 Beta。这个阶段优先补 demo dataset、demo account、quickstart、known limitations、feedback 入口、walkthrough 和发布前稳定性。

### 结果形态

1. 一条 full-chain walkthrough 能稳定跑通。
2. Demo dataset / demo account / quickstart 可用。
3. Known limitations 和 feedback 入口清楚。
4. 发布前的必过门禁和失败处理路径明确。

### 本阶段边界

不新增复杂 RAG 能力；只把已有主链做到可演示、可试用、可回归。

## Phase 4.0-3：Citation-backed Review Artifacts

### 核心思路

把 Review Draft、Notes、Compare 的输出推进到可交付研究材料：综述草稿、对比表、证据矩阵、引用清单和 known limitations。重点是产品化 artifact，而不是先上新框架。

### 结果形态

1. Review Draft 可从 KB / paper set 稳定生成。
2. 输出带 citation audit，unsupported / weakly supported claim 进入修复队列。
3. 用户可从草稿回跳到具体 evidence、paper 和 claim。
4. Compare / Notes 的结果能进入综述材料。

### 本阶段边界

不做通用文档编辑器重写；只围绕学术研究产物做最小闭环。

## Phase 4.0-4：Frontend Experience Craft

### 核心思路

对 v4.0 主研究流程做非常细致的前端体验和视觉打磨。重点不是重做信息架构，也不是再开一套页面，而是在既有 Dashboard / Search / KB / Read / Chat / Notes / Compare / Review 主链上，把视觉层级、信息密度、状态表达、动效、排版和空/错/加载态做到可对外展示。

### 结果形态

1. Dashboard、Search、KB、Read、Chat、Review 的主路径视觉语言统一。
2. 阻塞、处理中、证据不足、导入完成、可继续等状态有清晰视觉层级。
3. 页面首屏、卡片、侧栏、CTA、空状态、错误态、loading skeleton 均被逐页打磨。
4. 保持设计杂志感和科技感，但不引入新的并行设计系统。

### 本阶段边界

不重做 IA，不新增平行页面，不替换主技术栈；前端实现必须遵守 `docs/specs/design/frontend/DESIGN_SYSTEM.md`，涉及复杂文本布局时优先按 pretext 路径评估。

## Phase 4.0-5：Frontend Interaction Quality

### 核心思路

第二个前端打磨 phase 专门处理交互质量、响应式、可访问性、键盘路径、移动/窄屏、触控、性能感知和真实用户流畅度。它和 Phase 4.0-4 的区别是：4.0-4 偏视觉与表达，4.0-5 偏操作质量和体验可靠性。

### 结果形态

1. 核心操作不依赖 hover-only，可键盘访问，可触控执行。
2. Search import、KB papers、Read/Chat handoff、Review trace 等主路径有清晰焦点、返回、撤销或恢复体验。
3. 关键页面在桌面、窄屏和常见浏览器尺寸下可用。
4. 长列表、长回答、长任务进度有性能感知优化和用户反馈。
5. 前端 type-check、Vitest、核心交互测试和必要的浏览器 walkthrough 有回归证据。

### 本阶段边界

不引入全站重构，不把交互打磨扩大成新功能研发；只修真实 workflow 里的阻塞、摩擦和质量缺口。

## Phase 4.0-6：Academic RAG Optimization

### 核心思路

B 类技术升级保留为一个优化 phase。只在产品主链稳定后，引入 agentic evidence loop、corrective retrieval、Graph / global synthesis 等能力，目标是优化已有 workflow，而不是替换产品主链。

### 结果形态

1. retrieval confidence、claim verification、unsupported claim、degraded runtime 可触发下一步建议。
2. Chat / Review / Compare 使用同一 evidence action contract。
3. Graph / global synthesis 只进入 Review / Survey / Related Work，不替代 fact-level RAG。
4. 技术优化必须能在 Phase 4.0-7 的测试评测中证明收益。

### 本阶段边界

不训练 Self-RAG 同款模型，不整仓迁移外部框架，不新增第二套 agent runtime。

## Phase 4.0-7：Testing and Evaluation Gate

### 核心思路

B 类技术升级单独留一个测试评测 phase。它负责验证 v4.0 产品主链、Beta release、citation artifacts、两个前端打磨 phase 和 academic RAG optimization 的真实收益，避免“看起来更智能但不可证明”。

### 结果形态

1. Full-chain workflow test：Search -> Import -> KB -> Read -> Chat -> Notes -> Compare -> Review。
2. Product acceptance test：demo dataset、demo account、quickstart、known limitations、feedback。
3. RAG quality test：citation coverage、unsupported claim rate、retrieval confidence、degraded runtime。
4. Frontend quality test：视觉一致性、交互 walkthrough、响应式、可访问性、性能感知。
5. Release verdict 明确区分 `experiment-only`、`release-pass`、`blocked`。

### 本阶段边界

不追求一次性覆盖所有公开 benchmark；先保证本项目 v4.0 gate 可复现、可解释、可阻断。

## 5. Phase 顺序

| 顺序 | Phase | 是否可并行 | 阻断关系 |
|---|---|---|---|
| 1 | 4.0-0 Version Gate | 否 | v4.0 所有功能 phase 的前置 |
| 2 | 4.0-1 Productized Research Workflow | 否 | A 主线，先把连续研究流程打通 |
| 3 | 4.0-2 Beta Release Hardening | 部分 | C 主线，补演示、稳定性和反馈闭环 |
| 4 | 4.0-3 Citation-backed Review Artifacts | 部分 | A+C 交叉，形成可交付研究产物 |
| 5 | 4.0-4 Frontend Experience Craft | 部分 | 前端细致打磨一：视觉、状态、排版和展示质量 |
| 6 | 4.0-5 Frontend Interaction Quality | 部分 | 前端细致打磨二：交互、响应式、可访问性和性能感知 |
| 7 | 4.0-6 Academic RAG Optimization | 是 | B 优化 phase，只优化已稳定主链 |
| 8 | 4.0-7 Testing and Evaluation Gate | 是 | B 测试 phase，验证产品、前端质量和技术收益 |

## 6. 当前下一步

立即进入 `Phase 4.0-0`：

1. 固化 v4.0 版本目录和状态台账。
2. 回填 v3.0 已复测通过的 smoke 证据。
3. 对 v3.0 剩余缺口做 carry-forward 分类。
4. 跑治理脚本，确保 v4.0 主线没有破坏仓库边界。

## 7. Open Questions

1. Phase 4.0-1 的 workflow context 先做后端资源，还是先以前端 shell + existing run refs 承接。
2. Phase 4.0-2 的 Beta 资产是本地 demo 还是云端 demo 优先。
3. Phase 4.0-3 的 Review artifact 第一批支持 KB scope 还是 paper set scope。
4. Phase 4.0-4 的前端视觉打磨是否先从 Dashboard/Search/KB 开始，还是从 Chat/Review 开始。
5. Phase 4.0-5 的交互质量是否需要引入浏览器 walkthrough 作为硬门禁。
6. Phase 4.0-6 的优化优先做 corrective retrieval、agentic evidence action，还是 Graph/global synthesis。
7. Phase 4.0-7 的 release gate 是否直接纳入 GitHub workflow，还是先保留手动脚本。
