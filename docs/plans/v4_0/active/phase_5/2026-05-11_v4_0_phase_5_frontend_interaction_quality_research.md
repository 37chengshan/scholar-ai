# v4.0-5 研究文档：Frontend Interaction Quality

> 日期：2026-05-11  
> 状态：research  
> 对应执行计划：待创建  
> 上游总览：`docs/plans/v4_0/active/overview/18_v4_0_overview_plan.md`  
> 上游 Phase 4：`docs/plans/v4_0/active/phase_4/2026-05-08_v4_0_phase_4_frontend_experience_craft_research.md`

## 1. 研究问题

Phase 4.0-5 的目标不是继续做视觉 polish，也不是借机重做 IA，而是把 ScholarAI 主研究流程中的真实操作摩擦收口到可键盘、可触控、可窄屏、可恢复、可感知性能的交互质量基线。

本阶段要回答五个问题：

1. 当前真实代码里，哪些交互底座已经存在，可以直接承接。
2. 哪些主链页面仍然存在 hover-only、按钮假导航、窄屏挤压或状态反馈不足的问题。
3. 官方 React / Radix / MDN 路线里，哪些能力应该直接 adopt，哪些只应做薄封装扩展。
4. Phase 4.0-4 已完成视觉壳层后，Phase 4.0-5 的最小交付面应该是什么。
5. 哪些工作必须明确留给 Phase 4.0-7 测试评测 gate，而不能在本阶段伪装成“已经验证通过”。

## 2. 上游边界与仓库真相

### 2.1 本阶段的定位已经在 v4.0 总览中冻结

`docs/plans/v4_0/active/overview/18_v4_0_overview_plan.md` 已将 Phase 4.0-5 定义为：

1. 核心操作不依赖 hover-only，可键盘访问，可触控执行。
2. Search import、KB papers、Read/Chat handoff、Review trace 等主路径必须具备清晰焦点、返回、撤销或恢复体验。
3. 关键页面在桌面、窄屏和常见浏览器尺寸下可用。
4. 长列表、长回答、长任务进度必须有性能感知优化和用户反馈。
5. 前端 type-check、Vitest、核心交互测试和必要 walkthrough 要有回归证据。

这意味着本阶段的完成定义偏“交互可靠性”，不是“页面更好看”。

### 2.2 Phase 4.0-4 已完成，但只覆盖视觉与壳层

截至 2026-05-11，`PLAN_STATUS.md` 与 `23_v4_0_phase_4_execution_plan.md` 的仓库真相是：

1. `WorkspaceShell`、状态系统、typography/density 与主链页面拆分已经完成 closeout。
2. Phase 4.0-4 明确没有承诺响应式、可访问性和性能感知全量扫。
3. Phase 4.0-5 不能重复做视觉壳层，而应直接消费既有壳层去处理真实交互债务。

### 2.3 设计系统已提前给出 Phase 5 的底线

`docs/specs/design/frontend/DESIGN_SYSTEM.md` 已冻结以下规则：

1. 主干操作不能 hover-only。
2. 页面跳转应优先使用语义化 `<a>` / `<Link>`，禁止用 `<button onClick={() => navigate(...) }>` 模拟导航。
3. 三栏页面必须明确响应式行为，不能用粗暴的 `overflow-x-scroll` 解决拥挤。
4. 动画不能默认依赖 `transition-all`。
5. 主链工作区要保持 workspace shell，而不是退回通用 SaaS 布局。

Phase 4.0-5 的任务不是再定义这些规则，而是把它们落实到真实代码。

## 3. 当前实现基线

### 3.1 已存在、可直接承接的交互底座

仓库已经具备以下可直接 adopt 的能力：

1. `apps/web/src/app/components/layout/WorkspaceShell.tsx`
   - 已统一主链多栏壳层，适合作为桌面工作区 canonical layout。
2. `apps/web/src/app/components/Layout.tsx`
   - 已具备 `ScrollArea`、移动端 `Sheet`、侧边栏折叠持久化等基础设施。
3. `apps/web/src/features/kb/components/KnowledgePapersPanel.tsx`
   - 已接入 `react-window`，说明长列表虚拟化不是 Phase 5 的空白能力。
4. `apps/web/src/features/read/components/ReadWorkspace.tsx`
   - 已对窄屏辅助面板使用 `Sheet`，说明“桌面 inspector / 移动 drawer”模式已存在真实样例。
5. `apps/web/src/styles/global.css`
   - 已有 `:focus-visible` 与 `@media (hover: none) and (pointer: coarse)` 约束，说明 reduced hover 和键盘焦点样式已有全局入口。
6. `apps/web/package.json`
   - 已有 `react-resizable-panels`、`react-window`、Radix primitives、`motion`、`@chenglou/pretext`，不需要为本阶段再引新库。

### 3.2 当前最明显的交互债务

基于当前代码，Phase 5 需要优先处理以下真实问题：

1. **按钮假导航仍然广泛存在**
   - `Layout.tsx`、`KnowledgeWorkspaceShell.tsx`、`ReadWorkspaceScreen.tsx` 等位置仍有大量 `button + navigate(...)` 路径跳转。
   - 这与设计系统的“路由底线”直接冲突，也削弱了新标签页、语义和可访问性。
2. **主链局部仍有 hover-reveal 行为**
   - `MessageFeed.tsx` 中消息操作行仍以 `group-hover:opacity-100` 为主。
   - 部分列表和卡片动作的可见性仍明显偏向鼠标路径，不利于触控与键盘。
3. **窄屏/小屏约束仍不稳定**
   - `KnowledgeWorkspaceShell.tsx` 使用 `h-[calc(100vh-5rem)] min-h-[720px]`，并在多个动作按钮上使用 `hidden lg:inline-flex`。
   - 这说明 KB 工作区在窄屏下虽有壳层，但 inspector、操作入口和最小高度策略仍可能压缩或遮挡交互。
4. **性能感知仍然不够统一**
   - 列表虚拟化已落到 KB papers，但 Compare matrix、消息长流、跨页 tab 切换的 stale/pending 语义还没有 phase 级统一规范。
   - `overflow-x-auto` 在 Compare 和代码块中仍是常见兜底，但这不等于主路径交互质量已经完成。
5. **长任务与处理中状态的语义还不够一致**
   - 导入、review run、chat streaming 虽然都有状态表达，但“处理中 / 可继续 / 部分完成 / 证据不足”的交互恢复动作没有完全统一。

### 3.3 需要特别保留的既有正确方向

Phase 5 不应推翻以下已经正确的实现方向：

1. KB 论文列表虚拟化已经采用 `react-window`，应继续扩展而不是回退为全量渲染。
2. Read 面板的 `Sheet` 窄屏模式是正确样例，应推广到其他 inspector-heavy 页面。
3. `WorkspaceShell` 已是桌面主链 canonical shell，应围绕它定义交互规则，而不是再开平行容器。
4. `pretext` 只应服务复杂文本排版，不应被误用为通用交互修复工具。

## 4. Search-first 研究结果

本阶段不需要新引大型框架，重点是对现有与官方能力做 adopt / extend 决策。

| candidate | source | fit | decision | reason |
|---|---|---:|---|---|
| React `useDeferredValue` / `useTransition` / `startTransition` | React official docs | 5/5 | adopt | 适合 Search、tab、inspector 和长列表 refresh 的 stale-while-update 交互 |
| `react-resizable-panels` | upstream README | 5/5 | adopt | 已在仓库中使用，适合统一桌面多栏交互、持久化与 collapse 行为 |
| `react-window` | upstream README | 4/5 | adopt | 已落到 KB papers，适合继续覆盖高数据量列表与性能感知场景 |
| Radix primitives | Radix accessibility docs | 5/5 | adopt | Dialog、Tabs、ScrollArea、Sheet 的焦点和语义底座已经足够 |
| MDN `prefers-reduced-motion` / `hover` / `pointer` | MDN | 5/5 | adopt | 可作为动画降级、粗指针设备和 hover 能力分流的规范真源 |
| WAI live/status semantics | W3C/WAI APG | 4/5 | extend | 适合导入、review、streaming 的状态播报，但只需薄封装到现有状态组件 |
| `@chenglou/pretext` | existing dependency | 2/5 | extend narrowly | 只适合复杂文本布局，不应承担导航、键盘、响应式或焦点问题 |
| 新 UI/interaction framework | n/a | 1/5 | reject | 会与现有 Radix/Tailwind/CVA 路径冲突，并放大主链回归成本 |

## 5. 外部依据与采用结论

### 5.1 React 官方交互路径

React 官方文档对本阶段最关键的结论是：

1. `useDeferredValue` 适合保留旧内容，避免刷新时整块闪空。
2. `useTransition` / `startTransition` 适合把非阻塞更新显式建模成 pending state。
3. 稳定树位置与 `key` 控制应明确区分“保留状态”和“重置状态”。

对 ScholarAI 的含义：

1. Search、KB tab、Chat 右栏、Review trace 切换应优先走 stale-while-refresh，而不是先清空再重载。
2. inspector 展开/切换、筛选器切换、跨页 handoff 恢复时，pending 必须是用户可见状态，而不是静默卡顿。

### 5.2 Radix 与 WAI 语义边界

Radix 和 WAI 的启发不是“换组件”，而是：

1. Dialog / Sheet / Tabs / ScrollArea 的焦点、返回和键盘路径应复用既有原语。
2. 长任务状态应具有 `status` / `live region` 的语义，而不是只变颜色或只显示 spinner。

对 ScholarAI 的含义：

1. 导入中、索引中、review run 执行中、chat streaming 中等状态，要有统一的可读状态播报和恢复动作。
2. 窄屏 inspector 不应临时手搓，而应沿用 `Sheet` 类模式。

### 5.3 MDN 设备能力与动效分流

MDN 对 `prefers-reduced-motion`、`hover`、`pointer` 的规范意味着：

1. 不能假设所有设备都有 hover。
2. 不能假设复杂位移动画总是可接受。
3. 可以根据 coarse pointer / reduced motion 做策略分流，而不是把桌面细节硬塞给移动端。

对 ScholarAI 的含义：

1. 主干动作必须始终可见或至少有触控等价入口。
2. 大量 inspector、toolbar、card action 需要提供 coarse-pointer 友好版本。
3. 动画应以 opacity、color、small transform 为主，避免把体验建立在 hover reveal 或大位移上。

## 6. Phase 4.0-5 的研究决策

### 6.1 Adopt

本阶段应直接 adopt：

1. `WorkspaceShell + Sheet` 双模式
   - 桌面保留 resizable workspace，窄屏切换为 drawer/stack。
2. React stale-while-refresh 路线
   - `useDeferredValue`、`useTransition`、`startTransition`。
3. `react-window`
   - 继续用于高密度列表，而不是退回非虚拟化大列表。
4. Radix focus / keyboard primitives
   - Tabs、Dialog、Dropdown、Sheet、ScrollArea 全部延续语义底座。
5. MDN media features
   - 以 `hover` / `pointer` / `prefers-reduced-motion` 作为交互降级规则真源。

### 6.2 Extend

本阶段应在现有底座上做薄封装扩展：

1. `Link-first navigation`
   - 为主路径卡片、列表项、侧栏入口建立统一的 linkable wrapper，减少 `button + navigate()`。
2. `InteractionState family`
   - 在 `UnifiedFeedbackState` 之上统一 `processing / partial / ready / retryable / continue` 的文案、CTA 和 live region 语义。
3. `Inspector responsive policy`
   - 为 Search / KB / Read / Chat / Review 冻结桌面 inspector 与窄屏 drawer 的一致规则。
4. `Action visibility policy`
   - 主干操作常驻，次要增强才允许 hover；需要给触控和键盘提供等价入口。
5. `Performance hint policy`
   - 长列表、长回答、后台刷新统一使用 stale、skeleton、busy badge 或 progress copy，而不是每页各写一套。

### 6.3 Avoid

本阶段明确不应做：

1. 不新引 UI 库、手势框架或整站响应式框架。
2. 不把 Phase 5 扩大成新功能研发或 IA 重做。
3. 不把 `pretext` 扩大成全站交互解决方案。
4. 不把 Phase 4.0-7 的验证结论提前写成“已通过”。
5. 不以 `overflow-x-auto` 作为复杂 workspace 的默认响应式答案。

## 7. 最小交付定义

Phase 4.0-5 的最小交付不应写成泛泛的“交互体验更好”，而应收口为以下五类能力：

1. **导航语义收口**
   - 主路径跳转从 `button + navigate()` 收敛到语义化 link-first 模式。
2. **主干操作常驻**
   - Chat、KB、Review、Compare 等关键操作不再依赖 hover 才能发现。
3. **Inspector 响应式一致**
   - 桌面三栏、窄屏 drawer、返回/关闭/恢复策略统一。
4. **性能感知一致**
   - stale refresh、虚拟化、streaming、长任务 busy state 采用一致的可见反馈。
5. **键盘与触控路径补齐**
   - 焦点、快捷返回、可达按钮、可读状态文本至少覆盖主研究链。

## 8. 建议的执行顺序

### 8.1 P0

优先处理：

1. `Layout.tsx`
   - 侧栏、主导航、最近会话、知识库列表的语义导航与移动端菜单一致性。
2. `KnowledgeWorkspaceShell.tsx`
   - inspector、tabs、quick actions、min-height 与窄屏行为。
3. `MessageFeed.tsx`
   - hover-reveal 操作、streaming 状态和复制/证据动作的触控等价入口。

### 8.2 P1

随后处理：

1. Search 结果刷新与 filter/pagination 的 stale/pending 语义。
2. Compare / Review 的长内容滚动、矩阵视图和 run trace 响应式策略。
3. Read / Notes / Chat 跨页 handoff 后的焦点落点与恢复动作。

### 8.3 P2

最后处理：

1. 可访问性细项补测
2. coarse pointer / reduced motion walkthrough
3. 浏览器级回归脚本补齐

这些属于本阶段 closeout 证据，不属于研究阶段的已完成项。

## 9. 风险

| risk | impact | mitigation |
|---|---|---|
| 继续沿用 `button + navigate()` | 路由语义、可访问性和新标签体验继续分裂 | 以 link-first wrapper 做渐进替换 |
| 只修视觉不修 hover-only | 触控和键盘路径仍然断裂 | 主干操作常驻化，hover 只做增强 |
| 只做断点 CSS 不做 inspector 策略 | 窄屏仍会出现遮挡、丢入口和状态漂移 | 冻结桌面/窄屏 shell policy |
| 各页各自实现 pending 状态 | 用户对“处理中/可继续/失败恢复”理解继续分裂 | 建立统一 interaction state family |
| 把验证阶段混进实现阶段 | 研究与执行范围失焦 | 浏览器 walkthrough 和 gate 结论留给 Phase 4.0-7 或本阶段 closeout |

## 10. 研究结论

Phase 4.0-5 不需要新框架，正确路径是：

1. 直接 adopt 现有 React、Radix、`react-resizable-panels`、`react-window` 和 MDN 设备能力规范。
2. 在既有 `WorkspaceShell`、`Sheet`、`UnifiedFeedbackState` 基础上做薄封装扩展。
3. 把真实债务聚焦到导航语义、hover-only、窄屏 inspector、性能感知和键盘/触控路径。
4. 执行时先修 P0 主链，再补 P1/P2 细项，最后把 walkthrough 与测试证据交给 closeout。

外部参考：

1. React `useDeferredValue`: <https://react.dev/reference/react/useDeferredValue>
2. React `useTransition`: <https://react.dev/reference/react/useTransition>
3. React `startTransition`: <https://react.dev/reference/react/startTransition>
4. React preserving/resetting state: <https://react.dev/learn/preserving-and-resetting-state>
5. `react-resizable-panels`: <https://github.com/bvaughn/react-resizable-panels>
6. `react-window`: <https://github.com/bvaughn/react-window>
7. Radix accessibility overview: <https://www.radix-ui.com/primitives/docs/overview/accessibility>
8. MDN `prefers-reduced-motion`: <https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion>
9. MDN `hover`: <https://developer.mozilla.org/en-US/docs/Web/CSS/@media/hover>
10. MDN `pointer`: <https://developer.mozilla.org/en-US/docs/Web/CSS/@media/pointer>
