# Phase 5.0-1 审查报告: 维度 E — 架构集成

## Executive Verdict

**PASS-WITH-WARNINGS**

研究文档的 token 架构设计（三层 base/functional/component）和五族分类（typography/color/spacing/motion/elevation）在架构层面是合理的。但存在三个需在执行前解决的架构风险：(1) UI 原语层的硬编码阴影值与新 token 冲突；(2) evidence/claim 状态色彩在前端/后端/研究文档三者之间存在 5-vs-3 数量不一致；(3) 3 周时间线低估了 UI 原语层 + Tailwind arbitrary values 的迁移工作量。

## Findings

| # | 严重度 | 影响 phase | 问题 | 建议修复 |
|---|---|---|---|---|
| E-1 | HIGH | 5.0-1 | **UI 原语层硬编码 hex 阴影值与 theme.css tokens 冲突。** card.tsx 使用 `shadow-[4px_4px_0_0_#FF3300]` hover `shadow-[6px_6px_0_0_#002FA7]`，button/input/textarea 使用 `shadow-[3px_3px_0_0_#09090b]`。这些值既不在 theme.css 的 39 个 token 中，也不在研究文档的 elevation 族 token 定义中。#FF3300 / #002FA7 / #09090b 三个色值与暖纸 palette (#d35400) 品牌色体系不一致。 | Week 1 建 token 时必须在 elevation 族中为 UI 原语定义 `--shadow-brutal-default` / `--shadow-brutal-hover` / `--shadow-brutal-focus` token，并在 Week 2 优先替换 UI 原语层。card.tsx 的 #FF3300/#002FA7 应决定是保留（作为彩蛋 accent）还是统一到 --color-accent。 |
| E-2 | HIGH | 5.0-1, 5.0-6, 5.0-9 | **evidence/claim 状态色彩在前端/后端/研究文档三者数量不一致。** 后端 `rag_v3/schemas.py` 定义 5 种 `support_status`：`supported` / `weakly_supported` / `partially_supported` / `unsupported` / `not_enough_evidence`。研究文档定义 3 个 `--color-evidence-*` token（supported/unsupported/partial）。前端 CompareCard.tsx 实际映射 4 种（supported→emerald-500, partially_supported→amber-500, unsupported→red-500, not_enough_evidence→muted-foreground/30），缺 `weakly_supported`。 | 研究文档应补齐 5 个 evidence token（与后端 support_status 1:1 对应），或在 functional 层映射 weakly_supported 到 partial。必须在 5.0-1 收口时统一定义，否则 5.0-6 Chat 的 evidence card 和 5.0-9 release gate 会各自猜测色彩语义。 |
| E-3 | HIGH | 5.0-1 | **59 处 Tailwind arbitrary hex values 散布在 TSX/TS 中，grep 替换无法覆盖所有语义。** 包括 `text-[#d35400]`、`bg-[#fdfaf6]`、`border-[#f4ece1]`、`bg-[#fffaf2]` 等。其中部分与品牌色一致（可用 token 替换），但 `bg-[#fffdf9]`（ToolCallCard.tsx）、`bg-[#fffaf2]`（ThinkingProcess.tsx）等是未纳入 token 体系的近似色。 | Week 2 必须先做一次全量 hex→token mapping 表（区分"可直接替换"和"需要新增 token"），再执行批量替换。不建议纯 grep 替换，应逐文件审查上下文语义。近似色（#fffaf2、#fffdf9、#fdfaf6 三者仅亮度微差）应统一到 --color-surface 或 --color-surface-subtle 一个 token。 |
| E-4 | MEDIUM | 5.0-1, 5.0-2 | **packages/ui 为空壳（仅 README.md），无共享组件需同步 token。** 这简化了 5.0-1 的迁移范围（只需改 apps/web），但如果 5.0-2 或后续 phase 打算把 UI 原语下沉到 packages/ui，需要提前在 5.0-1 的 token 文件结构中考虑可抽取性。 | 在 5.0-1 的 token 文件中添加注释标注"未来可下沉到 packages/ui"，确保 token 定义不依赖 apps/web 特有路径。theme.css 的 @import 路径应使用相对路径而非 alias。 |
| E-5 | MEDIUM | 5.0-1, 5.0-8 | **runtime contract 的 evidence 色彩语义未与前端 token 对齐。** `v5_0_runtime_contract_freeze.md` 定义了 `truthfulness_summary.supported_claims` / `unsupported_claims` 等字段，以及 `answer_mode` 三值枚举。前端需要将这些语义映射到视觉色彩，但研究文档的 `--color-evidence-*` token 仅覆盖 support_status 子集，未覆盖 `answer_mode`（full/partial/abstain）和 `confidence_level`（high/medium/low）的色彩映射。 | 研究文档 color 族应增加 `--color-answer-full` / `--color-answer-partial` / `--color-answer-abstain` 和 `--color-confidence-high` / `--color-confidence-medium` / `--color-confidence-low` functional tokens。这些在 5.0-6 Chat 精修时会被 reasoning-panel 和 tool-timeline 消费。 |
| E-6 | MEDIUM | 5.0-4, 5.0-5 | **pretext adapter 已安装但不感知设计 token。** `@chenglou/pretext` 已在 package.json 和 `apps/web/src/lib/text-layout/measure.ts` 中使用，但仅做高度测量。当 5.0-4/5.0-5 需要用 pretext 做 editorial 排版时，pretext 的排版参数（行高、字号、tracking）应从新 token 派生而非硬编码。 | 5.0-1 的 typography token 应预留 `--font-body-l` / `--leading-relaxed` / `--tracking-tight` 等作为 pretext adapter 的输入参数。在 token 文件中以注释标记哪些 token 会被 pretext 消费。 |
| E-7 | MEDIUM | 5.0-1 | **dark theme 实现策略未指定 Tailwind dark: 变体的切换机制。** 研究文档提到 `[data-theme="dark"]` selector 和 `Tailwind dark: 变体兼容`，但当前 tailwind.config.js 仅保留兼容性配置（content paths），无 darkMode 设置。Tailwind v4 的 @theme 指令下 dark theme 需要显式在 CSS 中用 `[data-theme="dark"]` 块重写变量。 | 在 Week 3 实现 dark.css 时，必须先确认 Tailwind v4 的 dark 变体策略（class-based vs data-attribute），并在 dark.css 中用 `@theme` 块为每个 functional token 提供 dark 值。建议在 Week 1 就做一个 PoC 验证 `[data-theme="dark"]` + `@theme` 的交互行为。 |
| E-8 | LOW | 5.0-1 | **landing 页 canvas 绘制（GlobalDragonBackground.tsx）有 12+ 处硬编码颜色值，无法被 CSS token 覆盖。** 这些是 canvas ctx.fillStyle / strokeStyle 赋值，不走 CSS 变量。 | 在验收标准中明确：canvas 绘制颜色不在 token 迁移范围内。如果需要 dark theme 支持 canvas，应通过 JS 读取 getComputedStyle 获取 token 值传入 canvas。 |
| E-9 | LOW | 5.0-1 | **AnnotationToolbar.tsx 使用 Material Design 标注色 (#FFEB3B, #FF5722, #2196F3, #4CAF50)，不属品牌 palette。** 这些是 PDF 标注功能色，语义正确（Yellow/Orange/Blue/Green 高亮色），不需要改为暖纸色系。 | 在 token 族中增加 `--color-annotation-*` component-level token（4 个），确保 dark theme 下标注色可见性。可推迟到 Week 3。 |

## Migration Risk Assessment

### 39→165 迁移的具体风险点

**1. 高风险：UI 原语层阴影值硬编码（4 个文件）**

| 文件 | 硬编码值 | 风险 |
|---|---|---|
| card.tsx | `#FF3300` (shadow), `#002FA7` (hover) | 与暖纸 palette 不一致；新 elevation token 不含这两个色值 |
| button.tsx | `#09090b` (shadow) | 可映射到 `--color-ink-900`，但需确认 dark theme 下行为 |
| input.tsx | `#09090b` (shadow), `#FF3300` (focus) | 同 card.tsx 的品牌色冲突 |
| textarea.tsx | `#09090b` (shadow), `#FF3300` (focus) | 同上 |

**缓解**：这些 UI 原语是全站复用的基础组件，修改影响面大。建议在 Week 1 建 token 时就定义好 `--shadow-brutal-*` 系列，并在 Week 2 第一天替换这 4 个文件，然后跑全量 vitest 确认无回归。

**2. 中风险：Tailwind arbitrary values（59 处）**

- `text-[#d35400]`：约 5 处，可直接替换为 `text-[var(--color-accent)]`
- `bg-[#fdfaf6]` / `bg-[#fffaf2]` / `bg-[#fffdf9]`：近似色需统一
- `border-[#f4ece1]`：约 3 处，可替换为 `border-[var(--color-muted)]`
- `bg-[#22c55e]` / `bg-[#3b82f6]` / `bg-[#8b5cf6]` / `bg-[#ef4444]`（ScopeBanner.tsx）：语义色需映射到新的 semantic token

**缓解**：先建 mapping 表，再按组件族批量替换。每批替换后跑 vitest + type-check。

**3. 低风险：inline style 对象（25+ 处 features 目录，25+ 处 app 目录）**

大部分 inline style 是布局相关（scrollBehavior、minHeight、paddingLeft 计算），不含颜色或品牌值。仅 2 处含颜色：
- `AnnotationToolbar.tsx:91` — `backgroundColor: c.hex`（标注色，属 E-9 范围）
- `ReadAssistantPanel.tsx:158` — 含 style block（需检查具体值）

**缓解**：inline style 布局值不需要迁移。含颜色的 inline style 极少，可在 Week 2 顺带处理。

**4. 风险总结矩阵**

| 风险类型 | 数量 | 自动化可行性 | 建议策略 |
|---|---|---|---|
| UI 原语 hex 阴影 | 4 文件 | 低（需语义判断） | 人工逐文件审查 |
| Tailwind arbitrary hex | 59 处 | 中（grep + 替换，但需逐处确认近似色） | mapping 表 + 半自动替换 |
| Canvas 硬编码颜色 | 12+ 处 | 不适用 | 排除出迁移范围 |
| CSS vars (theme.css) | 39→165 | 高（新增为主） | 直接新增，旧值 alias |
| inline style 颜色 | 2 处 | 高 | 顺带处理 |

## Phase Dependency Check

### 5.0-1 与后续 phase 的接口清晰度

**接口定义充分的方面：**

1. **Token 文件结构**已明确定义（`tokens/typography.css` + `color.css` + `spacing.css` + `motion.css` + `elevation.css`），后续 phase 只需 `@import` 或 `var(--*)` 引用。
2. **向后兼容策略**明确：旧 `--color-primary` 等保留为 alias。
3. **Tailwind 消费路径**明确：通过 `@theme` 继续消费 CSS vars，不需要改 tailwind.config.js。

**接口定义缺失或模糊的方面：**

| # | 缺失接口 | 影响 phase | 问题描述 |
|---|---|---|---|
| D-1 | token consumption guide | 5.0-2 ~ 5.0-6 | 研究文档未定义后续 phase 如何"接入"新 token 的具体流程。例如 5.0-2 WorkspaceShell v2 是直接用 functional token，还是需要先建 component token？建议在 5.0-1 closeout 时输出一份 `token-usage-guide.md`。 |
| D-2 | pretext adapter token input spec | 5.0-4, 5.0-5 | pretext 已安装（`^0.0.6`），`measure.ts` 已使用。但 5.0-4/5.0-5 的 pretext editorial 排版需要哪些 typography token 作为输入参数，研究文档未明确定义。 |
| D-3 | dark theme 组件覆盖范围 | 5.0-2, 5.0-6 | dark.css 的覆盖范围是仅 functional tokens，还是包含 component tokens（如 `--chat-bubble-bg`）？如果 5.0-6 Chat 精修需要 chat 专属 component token 的 dark 变体，是 5.0-1 负责还是 5.0-6 负责？ |
| D-4 | anti-template 验收标准量化 | 5.0-2 | 研究文档提到"KB list / Search / Notes sidebar 无 uniform card grid 反例"，但未定义如何量化检测。5.0-2 布局改动时如何判断是否违反 anti-template 策略？ |

### 后端 phase 6 runtime contract 对齐检查

| 前端 token | 后端字段 | 对齐状态 |
|---|---|---|
| `--color-evidence-supported` | `support_status: "supported"` | 对齐 |
| `--color-evidence-unsupported` | `support_status: "unsupported"` | 对齐 |
| `--color-evidence-partial` | `support_status: "partially_supported"` | **部分对齐** — 缺 `weakly_supported` 和 `not_enough_evidence` 的专属 token |
| `--color-answer-*` (缺失) | `answer_mode: "full" \| "partial" \| "abstain"` | **未对齐** — 前端无 answer_mode 色彩 token |
| `--color-confidence-*` (缺失) | `confidence_level: "high" \| "medium" \| "low"` | **未对齐** — runtime contract 要求前端用不同色彩区分，但无 token 定义 |
| (无对应) | `degraded: boolean` | runtime contract 要求"degraded 指示器"，研究文档未定义 `--color-degraded` |

## 3 周实施计划现实性评估

### Week 1: Token 建设 — **现实但紧凑**

- 建 5 个 token 文件 + theme.css 重构为 @import：**可行**（纯新增 + 重构）
- 总量约 165 个 token 定义，工作量约 3-4 天
- **风险**：oklch 色阶生成（9 阶 × 3 族 = 27 色）需要精确调色，不能纯靠公式
- **建议**：Week 1 末尾必须跑 vitest + type-check 确认 token 引入无破坏

### Week 2: 全站接 Token — **时间不足，建议延长到 1.5 周**

- 59 处 Tailwind arbitrary hex 需逐处审查语义（不可纯 grep 替换）
- 4 个 UI 原语文件需修改 + 全量回归测试
- near-approximate 色值（#fffaf2/#fffdf9/#fdfaf6）需统一决策
- **关键瓶颈**：card.tsx / button.tsx / input.tsx / textarea.tsx 是全站基础组件，修改后影响面不可预测
- **建议**：将 Week 2 拆为 "2a: UI 原语 + 基础组件"（3天）+ "2b: feature 页面 + 近似色统一"（4天）

### Week 3: Dark + Anti-template — **时间不足，建议延长到 1.5 周**

- dark.css 是全新文件，需要为所有 functional token 定义 dark 值
- `[data-theme="dark"]` + Tailwind v4 @theme 的交互需 PoC 验证
- anti-template 视觉策略需要实际修改 3 个页面（KB/Search/Compare）
- **建议**：dark theme PoC 移到 Week 1 末尾，Week 3 专注 dark 完善 + anti-template 落地

### 总体评估

**3 周完成全部 9 项验收标准是乐观估计。建议调整为 3.5-4 周**，具体：
- Week 1（5天）：token 建设 + dark PoC
- Week 2a（3天）：UI 原语 + 基础组件 token 接入
- Week 2b（4天）：feature 页面 token 接入 + 近似色统一
- Week 3（5天）：dark theme 完善 + anti-template
- Week 4（3天）：buffer + 验收回归

## v4.0 phase_4/5 残留处理检查

**已正确处理：**
- PLAN_STATUS.md 已将 v4.0 phase_5 标为 `superseded-by-v5.0`，说明清晰
- v4.0 phase_5 的 P0 切片已完成，P1-P4 不再单独推进
- WorkspaceShell v1 代码仍在使用中（6 个页面引用），v5.0-2 将升级为 v2

**需注意：**
- WorkspaceShell.tsx 当前无 `superseded` 注释标记。建议在 5.0-1 执行时，在 WorkspaceShell.tsx 头部添加 `// v5.0-2 will supersede this layout with responsive stacking + density system` 注释，明确迁移意图
- magazine.css 的 524 行 landing 资产需用 `.magazine-landing` scope 限域（研究文档已提到），但未指定具体 selector 策略（BEM 前缀 vs scope class vs CSS layer）

---

*审查人: 架构集成审查员 (dimension E)*
*审查日期: 2026-05-31*
*输入文档: 2026-05-31_v5_0_phase_1_design_system_v2_research.md*
