# ScholarAI 前端设计与 Design System 综合审计报告

**审查日期**：2026-04-29
**覆盖范围**：应用页面界面 (`apps/web/src/app` 等核心路由)、业务组件库及 `DESIGN_SYSTEM.md`。

---

## 1. 核心审计结论 (Executive Summary)

ScholarAI 的前端已经在 Landing 页面确立了极具辨识度的高级视觉语言（报刊杂志风、暖色纸张纹理、高对比排版）。但**当前应用内部缺乏一致的约束**，导致“外表华丽但内部结构脆弱”。
主要风险可以归结为三点：
1. **多套平行的 UI 组件泛滥**：同一种概念（如搜索卡片、聊天容器、细节面板）存在多种平行实现（Legacy / V2 / Tool 变体并存）。
2. **重交互逻辑被隐藏或写错**：大量依赖 Hover 才能展示的关键操作，极度破坏移动端与触屏体验。大量应该用 `<Link>` 跳转的地方被错误地写成了 `<button onClick={...}>`。
3. **巨型“上帝”页面难以维护**：Chat、Read 和 Notes 页面的单文件代码量在 600~1000 行之间，状态与视图高度耦合。

如果不将控制规则写入 `DESIGN_SYSTEM.md` 中进行强制卡点限制，后续单纯的“视觉美化”只会增加系统的维护成本。

---

## 2. 精确到每个页面的优化建议 (Page-Level Optimizations)

### 2.1 外部与展现页面 (Landing & Auth)

*   **Landing (落地页)**
    *   **问题**：过度设计导致存在大量“假交互”，比如许多包含 `href="#"` 的无意义动作（“完整技术白皮书” 等按钮没有实际目标）。宽泛的 `transition-all` 动画让交互显得拖泥带水。
    *   **建议**：
        1. 清理没有实际产品映射的占位按钮（Empty States Action），避免损伤产品的工具信任感。
        2. 将 `transition-all` 替换为精确的 `transition-transform duration-200` 等具象动画。
        3. 对所有交互转盘（Testimonials）增加显式的 `aria-label`。
*   **Auth (登录 / 注册 / 找回密码)**
    *   **问题**：页面承载了过多“极客渲染”和装饰性系统日志。登录是一个高意图的任务，过多复杂的布局导致移动设备下的表单阅读体验下降。
    *   **建议**：大幅缩减此页面的装饰性内容（去掉无关的 Terminal 日志戏码）。聚焦表单本身，保持品牌主次分明，加快表单的响应与提交速度。

### 2.2 工作台入口与结构页面 (Dashboard & Search)

*   **Dashboard (控制台 / 个人首页)**
    *   **问题**：界面的视觉语言向普通的 SaaS 面板“妥协”，丢失了 Landing 页那套非常好看的排版主轴。最大的问题是几乎所有的导航卡片都被写成了 Button 路由（无法在新标签页打开）。
    *   **建议**：重构仪表盘网格，利用杂志化的卡片隐喻展示最近浏览、搜索历史。强制将页面进入链路改为 `<a>`（在 React / Next 体系内为 `Link`）。
*   **Search (搜索交互)**
    *   **问题**：搜索界面包含视觉可见但缺乏上下文的提交按钮。结果面板的收藏/导出等操作**高度依赖 Hover 显示**。右侧监控栏（Inspector）塞入了部分静态假数据伪装成动态指标。
    *   **建议**：
        1. 剥离并移除所有非真实的监控指标。
        2. 每个搜索卡片的“主操作”必须脱离 Hover 常驻可视。辅助操作可在 Hover 中高亮，但默认状态也不应完全隐藏。

### 2.3 核心生产力页面 (Chat, Knowledge Base, Read, Notes)

这些页面是整个系统的痛点，通常代码都在 **600～1000行** 左右，维护极度困难。

*   **Chat (智能对话)**
    *   **问题**：当前的 `ChatWorkspaceV2` 过度肥大，既接管网络流连接、又负责状态管理、还在一堆条件语句渲染各种浮动面板。并且存在 `ChatLegacy.tsx` 这样的冗余文件。
    *   **建议**：
        1. 清理删除全部 Legacy 代码。
        2. 强制拆分为 `Composer`（输入器）、`Feed`（消息流）、`ContextSidebar`（上下文控制）。把网络收发（Streaming Hook）提炼出单独的作用域。
*   **Knowledge Base (知识库结构)**
    *   **问题**：列表与卡片模式在此单页中逻辑交织。顶部的操作栏拥有过高的视觉密度。详情页存在 V2 和 Legacy。合并后的视图太容易卡顿。
    *   **建议**：删除重复实现。对动辄显示数百项引用来源的知识库列表执行**列表虚拟化（Virtualization）**，以避免在大量渲染时导致主线程阻塞。操作栏的次级选项收纳进入标准 `DropdownMenu`。
*   **Read & Notes (文献阅读与综合笔记)**
    *   **问题**：这两个组件各自承接了拖拽布局、Markdown 解析、全屏状态切换和草稿保存同步等海量交互副作用，内部的依赖数组（`useEffect`）极为繁杂。
    *   **建议**：提取所有“偏好状态”（如面板宽、侧边栏开闭、暗/亮模式偏好）到全局/本地持久化（LocalStorage/IndexedDB 配合 Zustand 或 Context），而不是把它们卡死在具体页面的 Local State (useState) 里。移除 Hover 才能删除笔记的交互灾难。

---

## 3. `DESIGN_SYSTEM.md` 针对性优化与增补建议

您当前的 `DESIGN_SYSTEM.md` 只有视觉（Typography / Tokens）和基础组件清单，缺乏**防止系统代码劣化的架构级底线规约**。建议立刻在 `DESIGN_SYSTEM.md` 中补充下述内容：

### 3.1 增加“唯一数据源原则” (Canonical Implementation Rule)
明确声明禁止私自建立平行组件。在文档中确立白名单机制：
*   **规定**：“凡涉及 `SearchResultCard`、`ThinkingDetailModal`、`StepTimeline` 等全局性复合业务卡片，**永远只允许存在一份代码实现**，必须抽离在通用 `components`，禁止在 Feature 内进行 Fork，防止 UI 更新断层。”

### 3.2 增加“重交互与可访问性”黄金法则 (Interaction & Semantics)
这是导致前端“华而不实”的元凶点。需写入设计系统的强制条例：
*   **路由底线**：禁止使用 `<button onClick={() => navigate(url)}>`，必须使用符合语义的 Web 原生行为或框架提供的 `<Link>`。
*   **反 Hover 依赖**：对于用户的“主干路径”操作和“破坏性删除”操作，**绝不允许仅在 Hover 时显现**。它们必须常驻，或者以次级变体（Muted）常驻。Hover 的存在只是为了反馈视觉聚焦。

### 3.3 补全“架构解耦声明” (Page Boundaries limitation)
*   **巨石页面拆分协议**：规定一个业务级 Page Root 不应该超过 ~400 行。超过的部分必须按照：
    *   Layout Shell (纯壳与排版占位)
    *   State Controller (数据钩子组合)
    *   Presentational Sections (各类只关心 prop 收发的纯面板) 进行拆分。

### 3.4 响应式与布局原语具象化 (Layout Primitives & Responsive)
*   现有的 `Sidebar-Main-Panel` 结构必须沉淀出一组类似 `<AppShell>`, `<AppSidebar>`, `<AppContent>` 的原语代码模板。
*   确立 Mobile 下是转换为 Drawer 还是垂直流栈（Column Stack），在 `DESIGN_SYSTEM.md` 的 Layout Rules 里固定断点对应关系。

---

## 4. 执行路线图 (Remediation Roadmap)

1. **Step 1：修补基础体验漏洞。** 全局搜索并替换错用的 Button-Navigation 以及在核心系统卡片上修复由于 Hover 导致的功能隐藏问题；清理无目的地 `href="#"`。
2. **Step 2：将规范固化到 DESIGN_SYSTEM。** 把上方第 3 节的内容同步进 `docs/specs/design/frontend/DESIGN_SYSTEM.md`，并在团队审查工具中生效。
3. **Step 3：执行组件去重清洗 (Component Canonicalization)。** 直接按名筛查找出所有被标注 Legacy 的组件，并完成删除/转正迭代。
4. **Step 4：上帝文件的肢解 (Stateful Surface Refactor)。** 作为长线战略，专门对 `Notes`、`Read`、`Chat` 三个 600行+ 的巨无霸文件施加结构性手术并持久化 UI 配置。