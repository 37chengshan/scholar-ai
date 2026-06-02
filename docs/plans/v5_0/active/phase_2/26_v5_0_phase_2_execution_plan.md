---
phase_id: 5.0-2
name: WorkspaceShell v2
owner: web-platform
status: in-progress
created_at: 2026-05-31
last_verified_at: 2026-05-31
research_doc: docs/plans/v5_0/search/2026-05-31_v5_0_phase_5_0_2_workspace_shell_v2_research.md
---

## Phase 5.0-2 WorkspaceShell v2 -- Execution Plan

### Objective

将 WorkspaceShell 从固定三栏桌面布局升级为响应式 stack（desktop 三栏 / tablet 两栏 / mobile 单栏），集成 Lighthouse CI 和 bundle budget enforcement（主入口 gzip <= 500KB），并为主要页面补全 skeleton / loading / empty / error 四态覆盖。

### Pre-conditions

| 条件 | 状态 |
|------|------|
| T0 安全修复（SSRF + XSS + CSS 注入） | **已完成**（研究阶段已修复并验证） |
| SSRF DNS Re-TOCTOU 缓解 | **已分配** -- 后续 Phase 加入 resolver 级缓存 |
| SSRF redirect bypass 缓解 | **已分配** -- 后续 Phase 加入 redirect 链 IP 校验 |
| MarkdownEditor ARIA 无障碍 | **已跟踪** -- 作为 T10 子任务 |

---

### Wave 1: Foundation（无依赖，可并行）

#### Task 1.1 -- 拆分 Layout.tsx

| 字段 | 值 |
|------|-----|
| **name** | T1: 拆分 Layout.tsx -- 提取 SidebarContent / SessionList / UserProfile |
| **files** | `apps/web/src/app/components/Layout.tsx`, `apps/web/src/app/components/layout/SidebarContent.tsx`（新建）, `apps/web/src/app/components/layout/SessionList.tsx`（新建）, `apps/web/src/app/components/layout/UserProfile.tsx`（新建） |
| **action** | 1. 从 Layout.tsx（585 行）中提取 `SidebarContent` 组件（侧边栏导航 + 会话分组 + 日期格式化逻辑）到独立文件<br>2. 提取 `SessionList` 组件（会话列表渲染 + 活跃会话高亮）<br>3. 提取 `UserProfile` 组件（头像 + 用户信息 + 设置入口）<br>4. Layout.tsx 仅保留路由壳 + 组合逻辑，降至 <300 行<br>5. 保持所有现有 import 和行为不变 |
| **verify** | `cd apps/web && npm run type-check` 通过；`npm run test:run` 无新增失败；Layout.tsx 行数 < 300 |
| **done** | Layout.tsx 从 585 行降至 <300 行；三个子组件独立存在且可单独测试 |
| **type** | refactor |

#### Task 1.2 -- 实现 useBreakpoint hook

| 字段 | 值 |
|------|-----|
| **name** | T2: 实现 useBreakpoint hook（扩展 use-mobile.ts） |
| **files** | `apps/web/src/app/components/ui/use-mobile.ts` |
| **action** | 1. 在 `use-mobile.ts` 中新增 `useBreakpoint()` hook，返回 `'mobile' \| 'tablet' \| 'desktop'` 三级断点<br>2. 断点阈值：mobile < 768px, tablet 768-1023px, desktop >= 1024px<br>3. 基于 `window.matchMedia` 实现，监听两个断点变化<br>4. 保留 `useIsMobile` 作为 `useBreakpoint` 的便捷包装（内部调用 `useBreakpoint() === 'mobile'`），确保 `sidebar.tsx` 等现有消费方零改动<br>5. 导出 `BREAKPOINTS` 常量供 CSS 变量和测试使用 |
| **verify** | `npm run type-check` 通过；`useIsMobile` 返回值不变（向后兼容）；`useBreakpoint` 在 resize 时正确切换 |
| **done** | `useBreakpoint` hook 存在且导出；`useIsMobile` 内部委托给 `useBreakpoint`；三个断点值正确 |
| **type** | feat |

#### Task 1.3 -- Bundle 分析工具集成

| 字段 | 值 |
|------|-----|
| **name** | T4: 集成 rollup-plugin-visualizer 分析主包依赖 |
| **files** | `apps/web/vite.config.ts`, `apps/web/package.json` |
| **action** | 1. `npm install -D rollup-plugin-visualizer`<br>2. 在 `vite.config.ts` 中添加 `visualizer` 插件配置，仅在 `--analyze` flag 时启用（`process.env.ANALYZE === 'true'`）<br>3. 运行 `ANALYZE=true npm run build` 生成 treemap 到 `apps/web/stats.html`<br>4. 分析 treemap 确认主包中 MUI/Emotion、react-markdown 系列、mermaid、katex、highlight.js 的实际 gzip 占比<br>5. 输出分析摘要，指导 T5/T6/T7 的拆分策略 |
| **verify** | `ANALYZE=true npm run build` 成功生成 `stats.html`；分析结果包含 chunk 大小和依赖树 |
| **done** | visualizer 已集成且可通过 flag 触发；主包依赖分析报告已产出 |
| **type** | chore |

---

### Wave 2: Responsive + Bundle Core（依赖 Wave 1）

#### Task 2.1 -- WorkspaceShell 响应式改造

| 字段 | 值 |
|------|-----|
| **name** | T3: WorkspaceShell 响应式 stack + Inspector overlay |
| **files** | `apps/web/src/app/components/layout/WorkspaceShell.tsx`, `apps/web/src/app/components/layout/InspectorDrawer.tsx`（新建） |
| **action** | 1. WorkspaceShell 消费 `useBreakpoint()` hook，根据断点切换布局策略<br>2. desktop (>=1024px)：保持现有三栏 `PanelGroup direction="horizontal"`，autoSaveId 按 layoutId 存储<br>3. tablet (768-1023px)：两栏（sidebar + main），Inspector 折叠为右侧 Drawer overlay，宽度 360px，点击 overlay 或按 Esc 关闭<br>4. mobile (<768px)：单栏 main，Sidebar 为 Sheet（复用现有移动端 Sheet 逻辑），Inspector 为全屏 overlay<br>5. 新建 `InspectorDrawer` 组件，接收 `inspector` ReactNode，用 `motion` 实现 slide-in 动画<br>6. PanelGroup 的 `autoSaveId` 按 breakpoint 分组存储，避免桌面和移动端互相覆盖面板尺寸<br>7. 保持 `WorkspaceShellProps` 接口不变，所有 7+ 个消费方零改动 |
| **verify** | `npm run type-check` 通过；桌面端三栏行为不变；resize 浏览器到 768px 以下时自动切换单栏；Inspector 在 tablet 以下以 Drawer 形式出现 |
| **done** | WorkspaceShell 在三种断点下正确响应；Inspector overlay 在 tablet/mobile 下可打开/关闭；现有消费方无需修改 |
| **type** | feat |

#### Task 2.2 -- Vite manualChunks 配置

| 字段 | 值 |
|------|-----|
| **name** | T5: 配置 Vite manualChunks 拆分 vendor chunks |
| **files** | `apps/web/vite.config.ts` |
| **action** | 1. 在 `vite.config.ts` 的 `build.rollupOptions.output` 中添加 `manualChunks` 配置<br>2. 拆分策略（基于 T4 分析结果调整）：<br>  - `vendor-react`: react, react-dom, react-router<br>  - `vendor-query`: @tanstack/react-query<br>  - `vendor-radix`: @radix-ui/* 系列<br>  - `vendor-motion`: motion (framer-motion)<br>  - `vendor-icons`: lucide-react<br>3. 设置 `build.chunkSizeWarningLimit: 500`（KB）以匹配预算<br>4. 运行 `npm run build` 验证拆分后主入口 chunk 大小 |
| **verify** | `npm run build` 成功；主入口 gzip <= 550KB（阶梯目标，最终目标 500KB 在 T6/T7 后达成）；无 chunk 重复 |
| **done** | manualChunks 配置已生效；主入口 gzip 降至 550KB 以下 |
| **type** | chore |

#### Task 2.3 -- Lighthouse CI 集成

| 字段 | 值 |
|------|-----|
| **name** | T9: 配置 Lighthouse CI（@lhci/cli + GitHub Actions） |
| **files** | `.lighthouserc.json`（新建）, `.github/workflows/lighthouse.yml`（新建） |
| **action** | 1. 创建 `.lighthouserc.json` 配置文件：<br>  - `staticDistDir: ./apps/web/dist`<br>  - `numberOfRuns: 3`（取中位数减少 CI 波动）<br>  - 断言：performance >= 0.8 (error), accessibility >= 0.9 (warn), best-practices >= 0.9 (warn), FCP <= 2000ms, LCP <= 2500ms, CLS <= 0.1, INP <= 200ms, csp-xss >= 0 (warn)<br>2. 创建 `.github/workflows/lighthouse.yml`：<br>  - 触发条件：push to main + PR to main<br>  - 使用 `treosh/lighthouse-ci-action@v11`<br>  - 先 `npm run build`（在 apps/web 目录），再运行 Lighthouse<br>  - 测试 URL：/, /dashboard, /chat<br>3. 本地验证：`npx @lhci/cli autorun` 通过 |
| **verify** | `.lighthouserc.json` 存在且格式正确；workflow YAML 语法有效；本地 `npx @lhci/cli autorun` 可执行（即使分数 warn） |
| **done** | Lighthouse CI 配置文件和 GitHub Actions workflow 已就位；本地 autorun 可执行 |
| **type** | ci |

---

### Wave 3: Bundle Deep + Four-State Foundation（依赖 Wave 2）

#### Task 3.1 -- 移除 MUI/Emotion 依赖

| 字段 | 值 |
|------|-----|
| **name** | T6: 移除 @mui/material + @emotion/* 依赖 |
| **files** | `apps/web/package.json`, `apps/web/package-lock.json` |
| **action** | 1. 确认 T4 分析结果：MUI/Emotion 在主包中的实际 gzip 占比<br>2. `npm uninstall @mui/material @mui/icons-material @emotion/react @emotion/styled`（如存在于 package.json）<br>3. `npm install` 重新生成 lockfile<br>4. `npm run build` 验证无构建错误<br>5. 对比移除前后主入口 gzip 大小 |
| **verify** | `npm run type-check` 通过；`npm run build` 成功；package.json 中无 @mui/* 或 @emotion/* 依赖；主入口 gzip 有所下降 |
| **done** | MUI/Emotion 依赖已移除；构建无错误；bundle 大小下降可量化 |
| **type** | chore |

#### Task 3.2 -- 重型库 Dynamic Import

| 字段 | 值 |
|------|-----|
| **name** | T7: 将 mermaid/katex/highlight.js/react-markdown 改为 dynamic import |
| **files** | 涉及使用 mermaid/katex/highlight.js/react-markdown 的组件文件（通过 `grep -r "from ['\"]mermaid\|from ['\"]katex\|from ['\"]highlight\|from ['\"]react-markdown" apps/web/src` 定位） |
| **action** | 1. 通过 grep 定位所有静态 import mermaid、katex、highlight.js、react-markdown 的文件<br>2. 将这些 import 改为 `const mod = await import('...')` 形式的 dynamic import<br>3. 在 dynamic import 处添加 `LoadingFallback` 作为 Suspense fallback<br>4. 确保 tree-shaking 正确排除这些库（检查 `npm run build` 的 stats.html）<br>5. 如果 `react-markdown` 已被主包静态引用但在非首屏组件中使用，将其包装为 lazy 组件 |
| **verify** | `npm run type-check` 通过；`npm run build` 成功；mermaid/katex/highlight.js/react-markdown 不再出现在主入口 chunk 中 |
| **done** | 四个重型库已从主包移至独立 chunk；主入口 gzip 进一步下降 |
| **type** | refactor |

#### Task 3.3 -- 四态组件标准化

| 字段 | 值 |
|------|-----|
| **name** | T10: 标准化四态组件 -- 修复 UnifiedFeedbackState 类型 + 统一 Skeleton 体系 |
| **files** | `apps/web/src/app/components/UnifiedFeedbackState.tsx`, `apps/web/src/app/components/Skeleton.tsx`, `apps/web/src/app/components/ui/skeleton.tsx` |
| **action** | 1. 将 `UnifiedFeedbackState.tsx` 中的 `any` 类型替换为严格接口：<br>  ```typescript<br>  interface FeedbackStateProps {<br>    variant: 'empty' \| 'loading' \| 'error' \| 'partial';<br>    title: string;<br>    description?: string;<br>    action?: { label: string; onClick: () => void };<br>    icon?: React.ReactNode;<br>  }<br>  ```<br>2. 统一 Skeleton 体系：以 shadcn `ui/skeleton.tsx` 为基础，废弃自定义 `Skeleton.tsx` 中的 CardSkeleton/ListSkeleton 等（迁移为基于 `ui/skeleton` 的组合）<br>3. 修复 MarkdownEditor ARIA 无障碍问题（研究审查要求）：为编辑器区域添加 `aria-label` 和 `role` 属性<br>4. 保留 `ChatSkeleton` 和 `DashboardSkeleton` 作为页面级骨架，但确保它们基于 `ui/skeleton` 构建 |
| **verify** | `npm run type-check` 通过；`UnifiedFeedbackState` 无 `any` 类型；所有 Skeleton 组件基于 `ui/skeleton.tsx` 构建 |
| **done** | UnifiedFeedbackState 使用严格类型；Skeleton 体系统一；MarkdownEditor ARIA 已修复 |
| **type** | refactor |

---

### Wave 4: Page States + Budget Enforcement（依赖 Wave 3）

#### Task 4.1 -- 页面级 Skeleton 态

| 字段 | 值 |
|------|-----|
| **name** | T11: 为主要页面创建 Skeleton 态 |
| **files** | `apps/web/src/app/components/Skeleton.tsx`（扩展）, 各页面组件（Dashboard, Search, KB, Analytics, Notes）的 lazy fallback 引用 |
| **action** | 1. 为以下页面创建对应 Skeleton 组件（基于 `ui/skeleton.tsx` 组合，严格匹配实际内容布局）：<br>  - `SearchResultsSkeleton`：搜索结果卡片列表骨架<br>  - `KnowledgeBaseSkeleton`：KB 详情页三栏骨架<br>  - `AnalyticsSkeleton`：图表 + 指标卡片骨架<br>  - `NotesSkeleton`：笔记列表 + 编辑器骨架<br>2. 将 Skeleton 组件作为各页面 `React.lazy` 的 `Suspense fallback`<br>3. 确保 Skeleton 尺寸与实际内容一致（防止 CLS）<br>4. Dashboard 和 Chat 已有 Skeleton，确认它们基于 `ui/skeleton` 并匹配当前布局 |
| **verify** | 每个页面的 Skeleton 在加载时显示且与实际内容尺寸匹配；无 CLS 闪烁 |
| **done** | 6 个主要页面均有对应 Skeleton 态；作为 Suspense fallback 应用到路由层 |
| **type** | feat |

#### Task 4.2 -- PageErrorFallback 组件

| 字段 | 值 |
|------|-----|
| **name** | T12: 创建 PageErrorFallback 组件（带 retry 指数退避） |
| **files** | `apps/web/src/app/components/PageErrorFallback.tsx`（新建）, `apps/web/src/app/components/ErrorBoundary.tsx`（更新）, `apps/web/src/app/routes.tsx` |
| **action** | 1. 创建 `PageErrorFallback` 组件：<br>  - 接收 `error: Error` 和 `resetError: () => void` props<br>  - 展示用户友好错误信息 + "重试" 按钮<br>  - retry 使用指数退避：首次立即，第二次 1s，第三次 2s，第四次 4s，之后 8s<br>  - 最大重试 5 次后展示"请联系支持"信息<br>2. 创建路由级 ErrorBoundary wrapper，在 `routes.tsx` 中为主要路由组包裹 ErrorBoundary + PageErrorFallback<br>3. 保持全局 ErrorBoundary 不变，路由级 ErrorBoundary 作为补充层 |
| **verify** | `npm run type-check` 通过；触发错误时 PageErrorFallback 正确展示；retry 按钮在多次点击后退避间隔递增 |
| **done** | PageErrorFallback 组件存在且导出；路由级 ErrorBoundary 已包裹主要页面；retry 退避逻辑正确 |
| **type** | feat |

#### Task 4.3 -- size-limit CI 预算检查

| 字段 | 值 |
|------|-----|
| **name** | T8: 配置 size-limit CI 预算检查（500KB gzip） |
| **files** | `apps/web/package.json`, `apps/web/.size-limit.json`（新建） |
| **action** | 1. `npm install -D size-limit @size-limit/preset-app`<br>2. 创建 `.size-limit.json`：<br>  ```json<br>  [<br>    {<br>      "path": "dist/assets/index-*.js",<br>      "gzip": true,<br>      "limit": "500 kB"<br>    }<br>  ]<br>  ```<br>3. 在 `package.json` 中添加 script: `"size": "size-limit"`<br>4. 本地运行 `npm run size` 验证<br>5. 在 `.github/workflows/ci-lite.yml` 中添加 size-limit 步骤（使用 `andresz1/size-limit-action@v1`） |
| **verify** | `npm run size` 可执行并输出主入口 gzip 大小；CI workflow 包含 size-limit 步骤 |
| **done** | size-limit 配置已就位；CI 中有 budget enforcement；主入口 gzip 在预算内或有明确的阶梯目标记录 |
| **type** | ci |

---

### Wave 5: Verification（依赖全部前置 Wave）

#### Task 5.1 -- 最终验证

| 字段 | 值 |
|------|-----|
| **name** | T13: 验证 bundle budget / Lighthouse 分数 / 四态覆盖率 |
| **files** | 无新增文件，执行验证命令 |
| **action** | 1. 运行 `cd apps/web && npm run build` 确认构建成功<br>2. 运行 `npm run size` 确认主入口 gzip <= 500KB（或记录当前值与阶梯目标）<br>3. 运行 `npx @lhci/cli autorun` 确认 Lighthouse performance >= 0.8<br>4. 运行 `npm run type-check` 确认零类型错误<br>5. 运行 `npm run test:run` 确认无新增测试失败<br>6. 浏览器 walkthrough：在 320px / 768px / 1024px / 1440px 四个断点下验证 WorkspaceShell 响应式行为<br>7. 验证四态：每个主要页面的 Skeleton / Empty / Error 态均可正确触发<br>8. 生成 Phase 5.0-2 closeout report |
| **verify** | 所有检查通过；closeout report 已生成并提交到 `docs/plans/v5_0/reports/` |
| **done** | Phase 5.0-2 所有子任务完成；bundle budget、Lighthouse、四态覆盖率均有验证证据 |
| **type** | test |

---

### Dependency Graph

```
Wave 1 (parallel):
  T1 (Layout 拆分) ──────────┐
  T2 (useBreakpoint) ────────┼──> T3 (WorkspaceShell 响应式)
  T4 (visualizer) ──────────┼──> T5 (manualChunks) ──> T8 (size-limit)
                             ├──> T6 (MUI 移除)
                             └──> T7 (dynamic import)
  T9 (Lighthouse CI) ──────── 独立

Wave 2 (depends on Wave 1):
  T3 (WorkspaceShell) ────── 依赖 T1, T2
  T5 (manualChunks) ──────── 依赖 T4
  T9 (Lighthouse CI) ──────── 独立

Wave 3 (depends on Wave 2):
  T6 (MUI 移除) ──────────── 依赖 T4
  T7 (dynamic import) ────── 依赖 T4
  T10 (四态标准化) ────────── 独立

Wave 4 (depends on Wave 3):
  T8 (size-limit) ─────────── 依赖 T5
  T11 (页面 Skeleton) ─────── 依赖 T10
  T12 (PageErrorFallback) ── 依赖 T10

Wave 5 (depends on all):
  T13 (最终验证) ──────────── 依赖 T1-T12
```

**关键路径：** T4 -> T5 -> T8 -> T13（bundle 优化链）

**可并行路径：**
- T1 + T2 + T4 + T9 + T10 在 Wave 1 可并行启动
- T6 + T7 在 T4 完成后可并行
- T8 + T11 + T12 在各自前置完成后可并行

### Success Criteria

| 指标 | 目标 | 验证方式 |
|------|------|---------|
| 主入口 gzip 大小 | <= 500KB（阶梯：先 550KB，再 500KB） | `npm run size` |
| Lighthouse Performance | >= 0.8 | `npx @lhci/cli autorun` |
| Lighthouse Accessibility | >= 0.9 (warn) | `npx @lhci/cli autorun` |
| Layout.tsx 行数 | < 300 行 | `wc -l apps/web/src/app/components/Layout.tsx` |
| WorkspaceShell 响应式 | 320/768/1024/1440 四断点正确 | 浏览器 walkthrough |
| 四态覆盖 | 6 个主要页面均有 Skeleton + Empty + Error | 代码审查 + 浏览器验证 |
| TypeScript 零错误 | `npm run type-check` 通过 | CI |
| 测试无新增失败 | `npm run test:run` 通过 | CI |
| CI 集成 | Lighthouse CI + size-limit 在 GitHub Actions 中 | workflow 文件存在 |

### Risk Mitigation

| 风险 | 缓解措施 |
|------|---------|
| Bundle 500KB 目标不可达 | 阶梯目标：Wave 2 后先达 550KB，T6/T7 后冲 500KB；如仍超，记录为 Phase 5.0-3 跟进项 |
| react-resizable-panels 移动端触摸冲突 | T3 中移动端直接跳过 PanelGroup，用单栏 + Sheet/Drawer 替代 |
| Lighthouse CI 环境波动 | `numberOfRuns: 3` 取中位数；performance 设为 error 阈值，其他设为 warn |
| Skeleton 与实际内容布局不匹配导致 CLS | Skeleton 组件严格参照实际内容的 DOM 结构和尺寸构建 |
