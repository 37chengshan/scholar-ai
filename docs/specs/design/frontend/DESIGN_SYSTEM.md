# ScholarAI Frontend Design System

## Purpose

定义 ScholarAI 当前前端真实设计系统的代码对齐规范，作为：

- 设计协作与 Figma MCP 对接真源
- `apps/web` 组件实现约束
- UI 审查、重构与新增页面时的统一参照

## Scope

本文件覆盖 `apps/web` 当前真实前端主路径中的：

- 主题令牌
- 字体与层级排版
- workspace 页面布局原语
- 基础组件与业务组件模式
- 图标、纹理、状态语义与设计落地规则

不覆盖独立产品策略、交互流程定义或后端契约；这些内容分别以架构、API 与产品计划文档为准。

## Source of Truth

- 主题令牌：`apps/web/src/styles/theme.css`
- 字体定义：`apps/web/src/styles/fonts.css`
- 类名合并工具：`apps/web/src/app/components/ui/utils.ts`
- UI 基础组件：`apps/web/src/app/components/ui/`
- 页面级业务组件：
  - `apps/web/src/app/components/`
  - `apps/web/src/features/search/components/`
  - `apps/web/src/features/kb/components/`
  - `apps/web/src/features/chat/components/`
- 路由层：`apps/web/src/app/pages/`
- 协作约束：`AGENTS.md`

## Rules

### 1. Design Direction

ScholarAI 当前视觉方向不是通用 SaaS，也不是冷色科技后台，而是：

- 暖纸张背景
- 学术阅读感
- 杂志化层级排版
- 橙色品牌强调
- 高对比、强结构、轻装饰

禁止在单页或单模块中私自演化出第二套主题，例如：

- 冷蓝科技风
- 紫色霓虹风
- 纯黑玻璃风
- 与纸张体系无关的渐变主视觉

页面必须优先复用现有 editorial / magazine 语言，而不是重新发明视觉系统。

### 2. Theme Tokens

颜色、字体、阴影、半径与布局变量以 `theme.css` 为唯一真源。Figma 稿、文档、组件实现都必须回对该文件。

#### 2.1 Core Colors

- `--color-primary: #d35400`
- `--color-primary-foreground: #ffffff`
- `--color-secondary: #e67e22`
- `--color-secondary-foreground: #ffffff`
- `--color-background: #fdfaf6`
- `--color-card: #ffffff`
- `--color-popover: #ffffff`
- `--color-muted: #f4ece1`
- `--color-muted-foreground: #7a6b5d`
- `--color-foreground: #2d241e`
- `--color-accent-foreground: #d35400`
- `--color-destructive: #d4183d`
- `--color-border: rgba(45, 36, 30, 0.1)`

#### 2.2 Support Tokens

- `--color-ring: oklch(0.708 0 0)`
- `--color-chart-1: oklch(0.646 0.222 41.116)`
- `--color-chart-2: oklch(0.6 0.118 184.704)`
- `--color-chart-3: oklch(0.398 0.07 227.392)`
- `--color-chart-4: oklch(0.828 0.189 84.429)`
- `--color-chart-5: oklch(0.769 0.188 70.08)`

#### 2.3 Radius and Shadow

- `--radius: 0.625rem`
- `--radius-sm: 0.375rem`
- `--shadow-paper: 4px 4px 0px 0px rgba(9, 9, 11, 1)`
- `--shadow-paper-hover: 6px 6px 0px 0px rgba(9, 9, 11, 1)`
- `--shadow-paper-active: 2px 2px 0px 0px rgba(9, 9, 11, 1)`

规则：

- 不允许在实现中绕过 token 直接硬写第二套主色。
- 允许局部使用 Tailwind 透明度修饰，例如 `border-primary/20`、`bg-primary/10`，前提是母色仍来自 token。
- 新增状态色时，先评估是否能由现有 token + alpha 组合表达；只有确实无法表达时才扩充令牌。

### 3. Typography

字体真源在 `fonts.css` 与 `theme.css`：

- `--font-serif: 'Playfair Display', 'Noto Serif SC', serif`
- `--font-sans: 'Outfit', sans-serif`
- `--font-mono: 'JetBrains Mono', monospace`

当前响应式字号变量：

- `--font-xs`
- `--font-sm`
- `--font-md`
- `--font-lg`
- `--font-xl`

使用约束：

- 页面主标题、论文标题、栏目标题、hero 文案优先使用 serif
- 导航、按钮、表单、说明文字、状态条优先使用 sans
- 结构化数据、统计值、ID、技术标签优先使用 mono
- 不要在同一块内容中无目的混用三套字体

推荐层级：

- 页面级标题：`font-serif` + `font-black` / `font-bold` + 紧 tracking
- 卡片标题：`font-serif` + `text-xl` 左右
- 工具栏/导航：`font-sans` + `uppercase` + `tracking-[0.14em~0.2em]`
- 辅助说明：`text-muted-foreground`

### 4. Layout Primitives

ScholarAI 当前页面不是单一 dashboard shell，而是 workspace shell + editorial panel 的组合。

#### 4.1 Global Layout Variables

- `--sidebar-expanded`
- `--sidebar-collapsed`
- `--right-panel-width`
- `--chat-max-width`
- `--composer-max-width`

#### 4.2 Page-Level Patterns

当前高频布局原语：

- 左侧主导航 + 中央工作区 + 右侧 inspector
- 顶部 sticky toolbar / sticky section header
- `PaperTexture` 作为全局纸张纹理背景
- 大量使用 auto layout 风格的 flex 垂直堆叠
- 内容区域以 `max-w-7xl`、`max-w-2xl`、`--chat-max-width` 控制阅读宽度
- **Layout Shell 抽象**：现有的 `Sidebar-Main-Panel` 结构必须沉淀为 `<AppShell>`, `<AppSidebar>`, `<AppContent>` 之类的底层布局原语，禁止在每个页面中去 Hardcode `flex flex-row h-screen` 等布局细节。

#### 4.3 Responsive & Mobile (响应式限制)
- 确立 Mobile 下视图转换：侧边栏必须转换为 Drawer 组件，或平铺为垂直流栈（Column Stack）。
- 任何含有三栏布局的页面必须明确定义 MD/LG 断点下的行为。不允许通过粗暴的 `overflow-x-scroll` 解决桌面形态的拥挤。

规则：

- workspace 页面优先延续现有三栏或双栏壳层，不要随意切回普通 marketing 页结构
- sticky toolbar 必须保持功能密度和滚动可持续性
- 阅读与问答区必须控制文本宽度，避免全屏横向摊开

### 5. Texture and Surface Language

`PaperTexture.tsx` 是当前真实视觉系统的一部分，不是临时装饰。

规则：

- 纸张纹理可用于页面级背景，不要叠加为高对比噪点前景
- 纹理默认低透明度，不能抢占正文可读性
- 卡片与主要容器仍以 `bg-card` / `bg-background` 为主，不要用纹理替代层次

### 6. Component System

#### 6.1 Base Components

基础组件目录：

- `apps/web/src/app/components/ui/`

约束：

- 基础组件遵循 shadcn/ui 风格组织
- 无障碍原语优先复用 Radix UI
- className 合并统一使用 `cn()`，定义在 `apps/web/src/app/components/ui/utils.ts`
- 变体优先使用 `class-variance-authority`

代表性基础组件：

- `button.tsx`
- `card.tsx`
- `dialog.tsx`
- `dropdown-menu.tsx`
- `input.tsx`
- `select.tsx`
- `tabs.tsx`
- `table.tsx`
- `tooltip.tsx`

#### 6.2 Business Components

业务组件不只在 `apps/web/src/app/components/`，还大量分布于 feature 目录。

高价值业务组件示例：

### 7. Component Canonicalization (唯一数据源原则)

为防止 UI 系统崩溃并产生多套平行的“组件孤岛”，特设立以下强制纪律：
- **禁止私自 Fork 组件**：凡涉及 `SearchResultCard`、`ThinkingDetailModal`、`StepTimeline`、`ToolCallCard` 等全局性复合业务卡片，**永远只允许存在一份代码实现**。
- **职责收边**：必须将其抽离并统管在公共的 `components` 目录下，严禁在 feature（如 `search/components/` 和 `app/components/` 中）形成相同语义模块的平行变体（Legacy / V2 / Tool 等），防止 UI 更新断层与修 Bug 时遗漏。

### 8. Interaction & Semantics (交互与可访问性底线)

当前在交互设计与 React 的实现间存在多处不严谨现象，导致前端难以维持稳健的可用性。此黄金法则将阻断“华而不实”：
- **路由底线 (No Fake Links / Dummy Buttons)**：涉及页面跳转、打开新窗口的操作，**必须**使用符合语义的原生 Web `<a>` 或 React Router 的 `<Link>`。**严禁**使用 `<button onClick={() => navigate(url)}>` 模拟导航（这剥挡了利用右键打开新标签、无障碍支持的能力）。删除无目的地占位 `href="#"`。
- **反 Hover 依赖 (Core Actions are Not Hidden)**：对于用户的“主干路径”操作（如编辑、查看详情）和“破坏性删除”操作（如取消分享、删除笔记），**绝不允许仅在 Hover 时显现**。这类操作必须一直常驻（可以弱化为次级静默色彩，如 Muted）。Hover 状态只应作为辅助视觉增强，不能作为存在的前提，因为这将破坏所有的触屏体验。
- **Motion (约束动画)**：限制全局性的 `transition-all` 并用作交互基石。所有属性动画必须具有明确的属性指向（如 `transition-colors`、`transition-transform`）。

### 9. Page Boundaries (巨石页面拆分协议)

产品级界面的脆弱很大程度来源于状态管理与视图排版的超级耦合。
- **规模协议**：单一业务级 Page Root 不应超过 ~400 行。
- **架构解耦**：超过此规模的 God Page（尤其是如 Notes / Read / Chat 这类重交互聚合页）必须依据以下关注点分离：
  - **Layout Shell**：仅仅处理纯外壳嵌套与排版区域划分，并下发给纯展示区。
  - **State Controller (Custom Hooks Layer)**：提取组合状态关联逻辑或网络数据挂载逻辑，而非全部堆在 `useEffect` 里。
  - **Presentational Sections**：将右边栏、聊天内容流等转化为只通过 Props 控制展示的无状态面板。
  - **Durable Preferences**：面板的开放闭合、用户偏好的布局尺度不应只写死在 `useState` 里，应该被全局偏好持久化管理。

- `apps/web/src/app/components/SearchResultCard.tsx`
- `apps/web/src/app/components/CreateKnowledgeBaseDialog.tsx`
- `apps/web/src/app/components/KnowledgeBaseCard.tsx`
- `apps/web/src/features/search/components/SearchWorkspace.tsx`
- `apps/web/src/features/search/components/SearchToolbar.tsx`
- `apps/web/src/features/search/components/SearchResultsPanel.tsx`
- `apps/web/src/features/kb/components/KnowledgeWorkspaceShell.tsx`
- `apps/web/src/features/kb/components/KnowledgePapersPanel.tsx`

规则：

- 新视觉模式若已跨页面复用，应优先沉淀为基础组件或清晰的业务组件模式
- 不要在页面文件中直接堆叠大量一次性样式，绕过组件层

### 7. Canonical UI Patterns

#### 7.1 Search Result Card

`SearchResultCard` 已经定义了 ScholarAI 对检索结果的 canonical 表达：

- 顶部微型来源 badge
- serif 标题
- 紧凑 authors 行
- 摘要使用斜体 + 左边框强化引用感
- 底部 actions / status / pdf link 分区

规则：

- 论文结果卡片优先延续该模式，不要新造完全不同的信息结构
- external/internal 差异优先通过状态与 action 表达，而不是换掉整张卡的视觉语言

#### 7.2 Knowledge Base Workspace

`KnowledgeWorkspaceShell` 定义了知识库空间的 canonical 壳层：

- 纸张背景
- 顶部标题区
- tabs 驱动的 papers / import / uploads / search / runs / review / chat
- 重点 CTA 位于右上角

规则：

- KB 级页面优先扩展这个 shell，不再平行造第二套 knowledge workspace
- 新增功能 tab 必须与现有 tabs 视觉节奏一致

#### 7.3 Research Continuity

ScholarAI 当前前端是一条连续研究链，而不是一组互不相干的工具页：

- `Dashboard` 只作为 command center，卡片只回答“现在状态 / 为什么要处理 / 点进去去哪”，不在首页执行任务。
- `Search` 只允许把结果收口为三类主动作：`Open Read`、`Add to KB`、`Continue in Chat`。纯外部发现未导入前，不得伪装成可读或可问状态。
- `KnowledgeWorkspaceShell` 必须在 tab 之上提供 readiness 摘要层，顺序固定为：导入接住 -> 去重决策 -> 解析索引 -> evidence ready -> Chat/Review ready。
- `Chat` 是唯一执行内核。所有跨页 handoff 进入 Chat 时，都必须保留 durable scope，并只做预填，不得自动发送。
- `Compare` / `Review` / `Analytics` 的首屏表达必须优先讲清楚“结论、证据、状态、下一步”，而不是先暴露底层模块或技术细节。

#### 7.4 Create Dialog

`CreateKnowledgeBaseDialog` 定义了当前创建类对话框模式：

- serif dialog title
- 基础信息在前，高级配置折叠在后
- label / counter / validation error 分层明确

规则：

- 新建类弹窗优先沿用“核心字段 + advanced collapse”模式
- 不要把复杂配置默认全部展开

### 8. Status Semantics

当前产品里有多组状态语义，设计层必须保持可读且一致：

- destructive / failed：红色系
- importing / processing：蓝色系
- metadata only / warning：琥珀系
- fulltext ready / completed：绿色系
- muted informational：纸张底色 + 深棕文字

规则：

- 状态文案必须优先真实表达系统状态，不要用“看起来更成功”的文案掩盖失败
- `metadata_only` 与 `fulltext_ready` 的视觉区分必须清晰
- `importing`、`failed`、`completed` 这类状态应延续 badge 语义，不要每页重新定义颜色

### 9. Motion and Interaction

当前前端使用 `motion`，但动效原则是：

- 以 section reveal、dialog enter、tab content enter 为主
- 不要滥用漂浮、弹跳、连续脉冲
- 所有动效都服务于层级感与状态反馈

规则：

- duration 以短促、可控为主
- layout shift 应最小化
- loading 态优先先给结构，再给动画

### 10. Icon System

图标库真源为 `lucide-react`。

规则：

- 图标命名使用 PascalCase
- 尺寸优先沿用现有比例：`h-4 w-4`、`h-5 w-5`、`w-3.5 h-3.5`
- 若与业务组件名冲突，可使用别名导入
- 不要混入第二套通用图标库

常用图标族：

- 导航/流程：`Search`、`ArrowLeft`、`ArrowRight`、`ChevronDown`
- 文档/阅读：`FileText`、`BookOpen`、`Library`
- 上传/导入：`UploadCloud`、`Download`
- 结构/分析：`Database`、`Layers`、`BarChart3`
- 交互/状态：`Check`、`CheckCircle2`、`RefreshCw`、`Trash2`

### 11. Library and Framework Constraints

当前前端系统依赖：

- React 18
- TypeScript 5
- Tailwind CSS v4
- Vite
- Radix UI
- Lucide React
- class-variance-authority
- tailwind-merge
- motion
- Zustand
- TanStack Query
- React Hook Form

实现约束：

- 状态管理分层必须清晰：本地状态、全局状态、服务端状态分开
- 设计系统文档不能要求一个当前并不存在的框架或组件库作为前提

### 12. Pretext and Text Layout

按 `AGENTS.md`，只要涉及复杂文字排版、文本绕排、动态重排、多栏流动、障碍物绕排，默认优先 `pretext` 路线。

仓库内真实入口：

- `apps/web/src/lib/text-layout/measure.ts`
- `apps/web/src/types/pretext.d.ts`

规则：

- 复杂文本布局先测量，再排版，再渲染
- 不要先做视觉拼贴，再补文本联动
- 纯静态展示且无复杂流动时，才允许不用 `pretext`

### 13. Figma Alignment Rules

本文件是 Figma MCP 对齐 ScholarAI 设计稿时的前端真源。

Figma 侧必须遵守：

- 优先对齐 `theme.css` 中真实 token，不手写第二套品牌色
- serif / sans / mono 的用途必须与代码一致
- workspace 页优先复用当前壳层，不要设计成 generic dashboard
- Search / KB / Chat / Review 等主链页面要保留“学术阅读 + 工具工作区”的混合气质
- 设计稿若新增可复用模式，必须能映射回组件或 token，而不是纯视觉特例

### 14. Anti-Patterns

以下做法禁止：

- 在单页直接引入紫色、冷蓝、霓虹等平行主题
- 用一组新的圆角、阴影、边框语言替代现有 paper/editorial 系统
- 将 workspace 页面改成 marketing landing page 结构
- 用浅灰低对比替代当前高可读正文体系
- 用“更好看”的文案掩盖 `failed`、`metadata_only`、`awaiting_user_action` 等真实状态

## Required Updates

- 变更主题令牌：同步更新 `apps/web/src/styles/theme.css` 与本文件
- 变更字体系统：同步更新 `apps/web/src/styles/fonts.css` 与本文件
- 变更基础组件约束：同步更新 `apps/web/src/app/components/ui/` 与本文件
- 新增全局布局原语或 workspace 壳层：同步更新本文件
- 新增前端设计协作约束：必要时同步更新 `AGENTS.md`

## Verification

- `cd apps/web && npm run type-check`
- 抽查 `theme.css`、`fonts.css`、`components/ui/`、`SearchWorkspace.tsx`、`KnowledgeWorkspaceShell.tsx` 与本文件是否一致
- 如有设计系统级改动，运行 `bash scripts/check-doc-governance.sh`

## Open Questions

- 是否需要把 design tokens 导出成更适合 Figma 同步的 machine-readable 格式
- 是否需要补一份 workspace primitives 清单，明确 hero / toolbar / inspector / panel / section 的组件映射
- 是否需要把状态语义整理为单独的 visual state spec，减少 `metadata_only` / `fulltext_ready` / `importing` 之类状态在多页面中的漂移
