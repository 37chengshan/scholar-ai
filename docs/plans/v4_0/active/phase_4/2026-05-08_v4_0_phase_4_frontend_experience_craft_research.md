# v4.0-4 研究文档：Frontend Experience Craft

> 日期：2026-05-08
> 状态：research
> 对应执行计划：`docs/plans/v4_0/active/phase_4/23_v4_0_phase_4_execution_plan.md`
> 上游总览：`docs/plans/v4_0/active/overview/18_v4_0_overview_plan.md`

## 1. 研究问题

Phase 4.0-4 的目标不是重做信息架构，也不是先处理响应式、可访问性和性能 gate，而是把 ScholarAI 已形成的主研究流程打磨到可展示、可解释、可连续使用的前端表达质量。

本阶段要回答四个问题：

1. 当前真实代码里，哪些视觉与状态表达能力已经存在，可以直接承接。
2. 哪些页面与组件正在拖累主链路的视觉一致性、信息密度和状态语义。
3. 在不引入第二套设计系统、不重做 IA 的前提下，哪些官方能力应直接 adopt，哪些只应做薄封装扩展。
4. Phase 4.0-3 仍未完成时，Phase 4.0-4 应如何推进，才不会把未冻结的 artifact contract 提前写死。

## 2. 上游边界与依赖真相

### 2.1 Phase 4.0-2 已给出可演示主链

截至 `2026-05-04`，Phase 4.0-2 的 repo 内真相是：

1. 主链已到 `walkthrough-complete / demo-ready`。
2. landing / login / KB / Read / single-paper Chat / Notes / Compare / upload/import workspace 已有浏览器 walkthrough 证据。
3. 当前最大的剩余风险，不是“页面完全不可用”，而是页面表达质量、状态一致性和 artifact 消费面仍不够稳定。

这意味着 Phase 4.0-4 不是救火修主链不可用，而是细化主链表达。

### 2.2 Phase 4.0-3 研究已落地，但执行未完成

当前 `docs/plans/v4_0/active/phase_3/2026-05-08_v4_0_phase_3_citation_backed_review_artifacts_research.md` 已存在，但这只代表：

1. citation-backed artifact 的研究边界已写清。
2. Review / Notes / Compare 的统一 artifact contract 仍未完成执行计划与代码收口。
3. 不能把 Phase 4.0-3 写成已完成，也不能假设 artifact-specific UI 语义已经冻结。

因此 Phase 4.0-4 的关键约束是：

1. 可以并行研究和实现基础视觉壳层、状态系统、workspace 面板语言。
2. 不应把 Review artifact、Compare matrix、citation audit 的最终展示 contract 过早固化。
3. 凡直接依赖 Phase 4.0-3 contract 的视觉精修，只能按“可兼容演进”设计，而不是按“上游已经收口”设计。

### 2.3 设计系统与 AGENTS 约束已经冻结

根据 `docs/specs/design/frontend/DESIGN_SYSTEM.md` 与仓库 `AGENTS.md`：

1. 视觉方向必须保持暖纸张背景、学术阅读感、杂志化层级排版、橙色强调和高结构密度。
2. 不允许私自引入第二套冷蓝、霓虹、纯黑玻璃风主题。
3. 主链工作区必须延续 workspace shell，而不是退化成 generic SaaS dashboard。
4. 涉及复杂文字排版、动态重排、多栏流动、障碍物绕排时，默认优先 `pretext` 路线。
5. 主干操作不能 hover-only，动画不能以 `transition-all` 为默认基石。

这意味着 Phase 4.0-4 不是重新寻找视觉方向，而是把现有方向真正落成全链路前端真相。

## 3. 当前实现基线

### 3.1 真实主链页面已经固定

根据 `apps/web/src/app/routes.tsx`，受保护主链页面已经固定为：

1. `dashboard`
2. `search`
3. `knowledge-bases`
4. `read`
5. `chat`
6. `notes`
7. `compare`
8. `settings`
9. `analytics`

Phase 4.0-4 的优先对象不是所有页面平均打磨，而是研究主链：

1. `Dashboard`
2. `SearchWorkspace`
3. `KnowledgeWorkspaceShell`
4. `Read`
5. `ChatWorkspaceV2`
6. `KnowledgeReviewPanel`

`Notes` 与 `Compare` 应作为第二优先级，跟随主链状态语义和 artifact 展示面一起收口。

### 3.2 页面规模与结构已经暴露脆弱点

当前页面体量已明显说明需要“先壳层、后视觉”：

1. `Dashboard.tsx` 约 `305` 行。
2. `KnowledgeBaseList.tsx` 约 `706` 行。
3. `Read.tsx` 约 `957` 行。
4. `Compare.tsx` 约 `974` 行。
5. `Notes.tsx` 约 `1482` 行。

而设计系统已明确：单一业务级 Page Root 不应长期维持 God Page 状态。
这意味着如果 Phase 4.0-4 只堆页面级一次性样式，会进一步放大维护成本和回归风险。

### 3.3 反馈状态组件已经出现双轨

当前 repo 里至少存在两套状态表达原语：

1. `apps/web/src/app/components/EmptyState.tsx`
2. `apps/web/src/app/components/UnifiedFeedbackState.tsx`
3. `apps/web/src/app/components/Skeleton.tsx`
4. `apps/web/src/app/components/ui/skeleton.tsx`

这说明“空态 / 错态 / loading / skeleton”的视觉语言还没有完全统一。
如果不先收口状态原语，逐页打磨会继续出现：

1. 文案口径不一
2. 卡片边框和留白不一
3. CTA 层级不一
4. loading 从 spinner、pulse、skeleton 到整页 blank 的表达漂移

### 3.4 多栏工作区已有技术底座，但未完全统一

当前依赖和代码里已经存在：

1. `react-resizable-panels`
2. `apps/web/src/app/components/ui/resizable.tsx`
3. `Read.tsx` 内部仍有手工 panel resize 逻辑
4. `ChatWorkspaceV2`、`KnowledgeWorkspaceShell`、`SearchWorkspace` 都在以各自方式维护多栏布局

这说明：

1. ScholarAI 并不缺多栏工作区能力。
2. 真正缺的是统一的 workspace shell、panel density、resize 持久化和 section hierarchy。

### 3.5 motion 与 pretext 都已接入，但还缺统一使用边界

当前 repo 已有：

1. `motion/react` 大量用于 `AnimatePresence`、卡片展开、面板 reveal。
2. `apps/web/src/styles/global.css` 中已有 `prefers-reduced-motion` 降级。
3. `@chenglou/pretext` 已安装，真实入口在 `apps/web/src/lib/text-layout/measure.ts`。

这意味着：

1. 不需要为 Phase 4.0-4 新引动画或文本布局库。
2. 需要补的是“何时该用，何时不该用”的 phase 级规则。

### 3.6 当前已验证残余问题会直接影响视觉打磨

`docs/plans/phase-text/2026-05-07_verified_residual_gaps_report.md` 已确认：

1. KB 列表和侧边栏仍暴露测试式种子内容。
2. compare-scoped chat 仍偏 summary-level evidence。

这意味着 Phase 4.0-4 不能只做表层美化；至少要保证：

1. demo-visible copy 不继续暴露测试痕迹。
2. “证据不足 / partial / summary-only” 的状态表达足够诚实，而不是被视觉包装掩盖。

## 4. 外部研究依据

| source | 采用结论 | 对 Phase 4.0-4 的约束 |
|---|---|---|
| React Suspense: https://react.dev/reference/react/Suspense | fallback 应轻量、可分层 reveal；已显示内容再次 suspend 时不应无条件整块闪回 | 主工作区要优先做 section-level skeleton / fallback，而不是 page blank |
| React `useDeferredValue`: https://react.dev/reference/react/useDeferredValue | 允许旧内容先保留，新内容后台更新，并用轻量 stale 提示说明状态 | 搜索结果、KB 列表、聊天侧栏刷新时优先保留旧内容，避免整块跳闪 |
| React `useTransition` / `startTransition`: https://react.dev/reference/react/useTransition / https://react.dev/reference/react/startTransition | 非阻塞更新应显式建模 pending visual state | panel/tab/filter/navigation 切换应有“正在更新但未阻塞操作”的表达 |
| React state preservation: https://react.dev/learn/preserving-and-resetting-state | 用稳定树位置保留状态，用 `key` 精确重置 | workspace 的 panel 宽度、draft、上下文面板不应在普通切换中意外丢失 |
| Tailwind v4 states & motion: https://tailwindcss.com/docs/hover-focus-and-other-states / https://tailwindcss.com/docs/transition-property / https://tailwindcss.com/docs/text-wrap | `focus-visible`、`motion-reduce`、明确的 `transition-*` 和文本换行工具应优先原生采用 | 视觉打磨必须建立在明确属性动画和可读文本换行之上，而不是 `transition-all` 和手工 hack |
| Radix accessibility + primitives: https://www.radix-ui.com/primitives/docs/overview/accessibility | Dialog、Tabs、ScrollArea 等应继续复用其语义与焦点管理 | 本阶段只能换皮和收口视觉，不应绕开 Radix 另写语义层 |
| CVA: https://cva.style/docs | Tailwind 变体应通过类型化 variant 收口，而不是把条件 class 散落在页面里 | 状态 badge、panel tone、CTA 层级、feedback shell 应统一进入 variant 模型 |
| Motion React accessibility: https://motion.dev/docs/react-accessibility / https://motion.dev/docs/react-use-reduced-motion | reduced motion 时应把大位移动画退化成 opacity 或更轻反馈 | 本阶段动效只能服务层级、进入和反馈，不能把炫技动画带入主链 |
| `react-resizable-panels`: https://github.com/bvaughn/react-resizable-panels | `autoSaveId` 与 separator keyboard semantics 适合复杂工作区 | 多栏 workspace 的 resize 应统一落到既有底座，而不是继续各页手搓 |
| WAI live/status semantics: https://www.w3.org/WAI/WCAG21/Techniques/aria/ARIA22.html / https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/ / https://www.w3.org/WAI/ARIA/apg/patterns/tabs/ | 静默状态、进度、modal、tabs 都有明确语义边界 | “处理中 / 证据不足 / 可继续 / 已完成” 的前端表达必须可读且语义正确 |

## 5. 研究决策矩阵

### 5.1 Adopt：直接采用现有技术路径

应直接 adopt 的能力：

1. `Radix UI + Tailwind v4 + CVA` 作为基础交互和视觉变体底座。
2. `react-resizable-panels` 作为 canonical workspace resizable shell。
3. `Suspense + useDeferredValue + useTransition/startTransition` 作为主链 stale-while-refresh 和 section loading 路径。
4. `motion` 的 reduced-motion 约束和轻量 reveal pattern。
5. WAI / Radix 的状态语义与焦点管理。

原因是：

1. 这些能力都已在 repo 或官方约束中出现。
2. 它们能直接解决 Phase 4.0-4 的视觉层级、状态表达和 workspace shell 问题。
3. 不需要引入第二套组件库或新框架。

### 5.2 Extend：在现有底座上做薄封装

应做薄封装扩展，而不是重写的能力：

1. 把 `EmptyState`、`UnifiedFeedbackState`、`Skeleton` 收口成统一 visual state family。
2. 把 `Search / KB / Read / Chat / Review` 的多栏结构收口成 `AppShell / WorkspacePanel / PanelSection / InspectorRail` 一类原语。
3. 为 `processing / importing / indexing / evidence_insufficient / partial / ready_to_continue` 冻结跨页 visual state spec。
4. 为主链面板引入可持久化的 resize / density / collapse 偏好。
5. 只在真正复杂文本块里，把 `pretext` 扩展成 artifact-aware text layout 能力。

这类扩展的原则是：

1. 只补统一性，不开第二套实现。
2. 只补可复用壳层，不在页面里继续堆一次性样式。

### 5.3 Avoid：本阶段明确不应做的方向

本阶段应明确 avoid：

1. 新引一套设计系统、UI 库或视觉主题框架。
2. 把 `pretext` 滥用到普通卡片、普通列表和常规摘要。
3. 用大位移、持续脉冲、`transition-all` 或 parallax 作为主链默认动效。
4. 借“视觉打磨”名义重做 IA、路由或 workflow semantics。
5. 假设 Phase 4.0-3 已完成，并把 artifact-specific 结构提前写死。

## 6. 本阶段的最小产品定义

Phase 4.0-4 的最小产品不是“所有页面都变好看”，而是以下五类能力稳定出现：

1. 主链页面共享同一套视觉层级和纸张式 editorial 语言。
2. `loading / empty / error / partial / insufficient evidence / continue` 的状态表达跨页一致。
3. workspace shell、panel、section header、CTA、rail、card 的密度和节奏统一。
4. 页面首屏可以对外演示，不暴露测试式 copy、破碎的 skeleton 或风格漂移。
5. 与 Phase 4.0-3 相关的 artifact 面板具备兼容演进的视觉容器，但不抢先冻结其最终 contract。

## 7. 执行顺序研究结论

### 7.1 可与 Phase 4.0-3 并行推进的部分

以下工作可与未完成的 Phase 4.0-3 并行推进：

1. global shell / workspace shell 原语
2. panel / card / section hierarchy
3. 统一 skeleton / empty / error / status family
4. typography、spacing、CTA hierarchy
5. resize persistence 和 panel density

因为这些工作主要处理展示壳层，而不是锁死 artifact contract。

### 7.2 应等待 Phase 4.0-3 进一步收口的部分

以下工作不应在上游未完成时过早定稿：

1. Review artifact bundle 的最终信息分区
2. citation audit 的完整状态文案和 CTA 优先级
3. compare matrix 与 review trace 的最终视觉 schema
4. evidence jump、claim repair、artifact export 等 artifact-specific surface

原因是这些地方直接依赖 Phase 4.0-3 的 contract 冻结。

### 7.3 页面优先级

建议页面优先级：

1. P0：`Dashboard`、`SearchWorkspace`、`KnowledgeWorkspaceShell`
2. P1：`Read`、`ChatWorkspaceV2`
3. P2：`KnowledgeReviewPanel`
4. P3：`Notes`、`Compare`

排序原则是：

1. 先收口全局主链第一屏和最大流量页。
2. 再处理高信息密度的阅读与问答区。
3. 最后处理更依赖 Phase 4.0-3 contract 的 artifact-heavy surface。

## 8. 本阶段不做什么

1. 不重做信息架构、路由和 workflow truth。
2. 不把响应式 / 可访问性 / 性能感知 sweep 扩大成 Phase 4.0-4 的主目标；这些属于 Phase 4.0-5。
3. 不修改 API contract、资源模型或后端 artifact schema。
4. 不补 Beta quickstart、demo dataset、walkthrough script；这些属于 Phase 4.0-2 / 4.0-7。
5. 不实现 Graph / global synthesis / corrective retrieval 等技术优化；这些属于 Phase 4.0-6。

## 9. 风险

| risk | impact | mitigation |
|---|---|---|
| Phase 4.0-3 contract 继续变化 | 过早定稿 artifact surface 会返工 | Phase 4.0-4 先做壳层与状态系统，artifact-specific UI 延后 |
| God Page 上继续堆样式 | 视觉打磨变成脆弱 patch | 先抽 shell / panel / state primitives，再回贴页面 |
| 状态组件双轨并存 | 用户看到的 loading/empty/error 语义继续漂移 | 优先统一 visual state family |
| 动效与字体各页自行演化 | 杂志感与科技感失真 | 冻结 motion、typography、CTA hierarchy 规则 |
| demo-visible seed copy 外泄 | 演示质量受损 | 把测试式 copy 清理纳入 P0 页面 polish |

## 10. 研究结论

Phase 4.0-4 应聚焦：

1. `workspace shell`
2. `visual state system`
3. `editorial typography and density`
4. `artifact-safe surface polish`

结论：

1. 当前 repo 已有足够的前端底座，不需要新引设计系统或组件库。
2. 最核心缺口不是“没有组件”，而是缺少跨页统一的视觉壳层、状态语言和 panel hierarchy。
3. Phase 4.0-4 可以在 Phase 4.0-3 未完成时启动研究，并先落不依赖 artifact contract 的基础视觉收口。
4. 但 Phase 4.0-4 绝不能把 Phase 4.0-3 的未完成部分包装成已冻结 UI 真相。
5. 只有在保持这条边界的前提下，前端打磨才不会再次偏成“视觉好看但主链事实失真”。
