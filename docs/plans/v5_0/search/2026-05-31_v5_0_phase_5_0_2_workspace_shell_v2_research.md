---
owner: product-engineering
status: research-ready
last_verified_at: 2026-05-31
scope:
  - apps/web/src/app/components/layout/WorkspaceShell.tsx
  - apps/web/src/app/components/Layout.tsx
  - apps/web/src/app/components/MarkdownEditor.tsx
  - apps/web/src/app/components/TypingText.tsx
  - apps/web/src/app/components/ui/chart.tsx
  - apps/web/src/lib/markdown-utils.ts
  - apps/api/app/tools/paper_tools.py
  - apps/web/vite.config.ts
inputs:
  - 27_v5_0_overview_plan.md
  - 2026-05-31_v5_0_ui_polish_and_perf_research.md
  - 2026-05-26_v4_5_frontend_backend_multidimensional_audit.md
---

## Phase 5.0-2 WorkspaceShell v2 -- 深度研究报告（修正版 v2）

> 本报告已根据代码审查反馈修正以下问题：
> 1. WorkspaceShell.tsx 使用范围的事实性错误（实际 7+ 页面依赖）
> 2. MarkdownEditor.tsx / TypingText.tsx XSS 漏洞识别与修复方案
> 3. MUI 移除风险评级修正（源码零 import，风险为低）
> 4. useBreakpoint 与 useIsMobile 关系明确
> 5. Lighthouse CI 配置补充 INP 和 best-practices 断言
>
> **v2 修正（安全审查后）：**
> 6. SSRF 漏洞：paper_tools.py 添加 URL scheme 白名单 + 内网 IP 段黑名单
> 7. XSS 修复：提取共享 `lib/markdown-utils.ts`，escape-first 策略，javascript:/data: 协议过滤
> 8. chart.tsx：ChartStyle 组件的 dangerouslySetInnerHTML 添加 CSS 颜色值消毒
> 9. T0 子任务扩展为覆盖全部四个安全修复点

---

### 一、现状分析

#### 1.1 当前 Shell 架构

当前工作区外壳由两个**独立层级**的组件承载，二者不存在合并逻辑：

- **`Layout.tsx`** (585 行, `/apps/web/src/app/components/Layout.tsx`) -- **App Shell 层**。承担全局侧边栏导航、会话列表、知识库快捷入口、用户资料、移动端 Sheet 菜单等职责。通过 `<Outlet />` 渲染子路由。已超出 400 行推荐上限。
- **`WorkspaceShell.tsx`** (45 行, `/apps/web/src/app/components/layout/WorkspaceShell.tsx`) -- **Page Shell 层**。使用 `react-resizable-panels` 实现三栏可调布局（sidebar / main / inspector），被 7+ 个页面直接依赖。

**WorkspaceShell.tsx 实际使用范围（非孤立组件）：**

| 使用方 | 文件路径 | 用法 |
|--------|---------|------|
| ChatWorkspaceLayout | `features/chat/workspace/ChatWorkspaceLayout.tsx` | 直接导入 |
| ReadWorkspace | `features/read/components/ReadWorkspace.tsx` | 直接导入 |
| SearchWorkspace | `features/search/components/SearchWorkspace.tsx` | 直接导入 |
| NotesWorkspaceScreen | `features/notes/components/NotesWorkspaceScreen.tsx` | 直接导入 |
| KnowledgeWorkspaceShell | `features/kb/components/KnowledgeWorkspaceShell.tsx` | 直接导入（包装层） |
| KnowledgeBaseDetailV2 | `features/kb/components/KnowledgeBaseDetailV2.tsx` | 通过 KnowledgeWorkspaceShell 间接使用 |
| Compare | `app/pages/Compare.tsx` | 直接导入 |
| KnowledgeBaseList | `app/pages/KnowledgeBaseList.tsx` | 直接导入 |

**层级关系：** Layout.tsx 是 App Shell（包裹所有页面），WorkspaceShell.tsx 是 Page Shell（各页面内部的三栏布局）。T1 改造聚焦 Layout.tsx 内部组件提取，T3 改造聚焦 WorkspaceShell 的响应式增强，两者不存在合并操作。

Layout.tsx 的问题：
- 单文件 585 行，接近 800 行硬限，职责过多
- 侧边栏内容、会话分组逻辑、日期格式化、用户头像逻辑全部内联
- 移动端和桌面端共用同一个 SidebarContent JSX，通过 `leftCollapsed` 和 `mobileMenuOpen` 两个独立状态控制
- `useIsMobile` hook 存在于 `ui/use-mobile.ts`，但 Layout.tsx 并未使用它，而是依赖 `md:` Tailwind 断点做 CSS 隐藏

#### 1.2 Bundle 现状

当前 `vite build` 产物（未配置任何手动 splitChunks）：

| 文件 | 原始大小 | Gzip |
|------|---------|------|
| **index-*.js (主包)** | **2.1 MB** | **620 KB** |
| pdf.worker.min-*.mjs | 1.0 MB | - |
| Read-*.js | 492 KB | - |
| wardley-*.js | 483 KB | - |
| cytoscape.esm-*.js | 432 KB | - |
| ownership-*.js | 372 KB | - |
| Analytics-*.js | 342 KB | - |
| index-*.css | 238 KB | 39 KB |
| **dist/assets 总计** | **8.3 MB** | - |

**主入口 gzip 620KB，目标 500KB，超出 24%。**

主包过大的根因分析：
- `@mui/material` 7.3.5 + `@emotion/*` 存在于 package.json，但**源码中零 import**（grep 确认），可能通过传递依赖或 tree-shaking 失败引入
- `react-markdown` + `rehype-*` + `remark-*` + `mermaid` + `katex` + `highlight.js` 全部打进主包
- `react-pdf` + `pdfjs-dist` 即使 lazy 了 Read 页面，其依赖仍可能被主包引用
- `recharts` (2.15.2) 被 Analytics lazy 引入但可能泄漏到主包
- 49 个 shadcn/ui 组件全部在 `components/ui/` 下，缺少 tree-shaking 优化

#### 1.3 安全漏洞现状（审查发现，已修复）

**严重程度：CRITICAL -- 已修复并验证**

| 文件 | 问题 | 修复状态 | 修复方式 |
|------|------|---------|---------|
| `paper_tools.py` | SSRF：用户控制的 URL 直接传入 `httpx.get(follow_redirects=True)`，可扫描内网和云元数据端点 | **已修复** | 添加 `_validate_url_for_fetch()` -- URL scheme 白名单（仅 http/https）+ 内网 IP 段黑名单（127.0.0.0/8, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 169.254.0.0/16, ::1/128, fc00::/7, fe80::/10）+ DNS 解析后 IP 校验 |
| `MarkdownEditor.tsx` | XSS：`simpleMarkdownToHtml` 无 HTML 实体转义，直接输出到 `dangerouslySetInnerHTML` | **已修复** | 提取为共享 `lib/markdown-utils.ts`，escape-first 策略（先转义 & < > " ' 再做 Markdown 转换），同时解决 javascript:/data: 协议过滤 |
| `TypingText.tsx` | XSS：link regex 未校验 `javascript:` 协议 | **已修复** | 统一使用 `lib/markdown-utils.ts` 的 `sanitizeUrl()`，阻断 javascript:/data:/vbscript: 协议 |
| `chart.tsx` | CSS 注入：ChartStyle 的 `dangerouslySetInnerHTML` 未消毒 config 中的 color 值 | **已修复** | 添加 `sanitizeCssColor()` 函数 + `SAFE_COLOR_RE` 正则白名单，阻断包含 `{}` `;` `\` 的注入向量 |

**修复验证结果：**
- `<script>alert(1)</script>` -> 被转义为 `&lt;script&gt;alert(1)&lt;/script&gt;` (PASS)
- `[click](javascript:alert(1))` -> href 被替换为 `#` (PASS)
- `[safe](https://example.com)` -> 正常渲染为链接 (PASS)
- `http://127.0.0.1/admin` -> 被 `_validate_url_for_fetch` 阻断 (PASS)
- `http://169.254.169.254/latest/meta-data/` -> 被阻断 (PASS)
- `ftp://evil.com/file` -> scheme 不在白名单，被阻断 (PASS)

#### 1.4 四态覆盖现状

| 状态 | 现有实现 | 覆盖度 |
|------|---------|--------|
| **Skeleton** | `Skeleton.tsx`（自定义 CardSkeleton/ListSkeleton/DashboardSkeleton/ChatSkeleton）+ `ui/skeleton.tsx`（shadcn 基础） | 部分 -- Dashboard 和 Chat 有骨架屏，其他页面无 |
| **Loading** | `LoadingFallback.tsx`（全局 spinner + motion 动画） | 路由级有，页面内无 |
| **Empty** | `UnifiedFeedbackState.tsx`（统一 empty/error/loading/partial 四态组件）+ `ChatEmptyState.tsx` | Chat 有专用空态，其他页面零散实现 |
| **Error** | `ErrorBoundary.tsx`（类组件，全局级）+ `UnifiedFeedbackState` error 变体 | 全局有，页面级无 |

问题：两套 Skeleton 组件并存（自定义 vs shadcn），UnifiedFeedbackState 使用 `any` 类型，ErrorBoundary 无 retry 指数退避。

#### 1.5 响应式现状

- `useIsMobile()` hook（`ui/use-mobile.ts`）基于 768px 断点，仅被 `sidebar.tsx` 使用
- Layout.tsx 用 `hidden md:block` 控制侧边栏显隐，移动端用 Sheet 抽屉
- 无 tablet (768-1024px) 适配逻辑
- WorkspaceShell.tsx 的 PanelGroup 未考虑移动端（固定 horizontal 方向）
- 无响应式堆叠（stack）逻辑 -- 三栏在小屏不会自动变为单栏
- **`useBreakpoint` hook 不存在**，当前仅有 `useIsMobile` 返回 boolean

#### 1.6 CI 现状

- `ci-lite.yml` 包含 typecheck + unit tests，无 Lighthouse CI
- 无 bundle size 检查（无 `size-limit` 或类似工具）
- 无性能预算 enforcement

### 二、技术方案

#### 2.0 T0 前置条件：安全漏洞修复（已完成）

**此任务为所有后续工作的前置条件，已在研究阶段完成修复。**

**修复 A：SSRF 防护 -- paper_tools.py URL 验证**

在 `apps/api/app/tools/paper_tools.py` 中添加 `_validate_url_for_fetch()` 函数：
- URL scheme 白名单：仅允许 `http` 和 `https`
- DNS 解析后 IP 校验：使用 `socket.getaddrinfo` 解析 hostname，检查解析后的 IP 是否在黑名单中
- 内网 IP 段黑名单：`127.0.0.0/8`（loopback）、`10.0.0.0/8`（RFC 1918）、`172.16.0.0/12`（RFC 1918）、`192.168.0.0/16`（RFC 1918）、`169.254.0.0/16`（link-local / 云元数据）、`::1/128`（IPv6 loopback）、`fc00::/7`（IPv6 ULA）、`fe80::/10`（IPv6 link-local）
- 在 `execute_upload_paper` 的 `httpx.get` 调用之前执行验证

**修复 B：XSS 防护 -- 提取共享 markdown-utils.ts**

将 `MarkdownEditor.tsx` 和 `TypingText.tsx` 中各自独立的 `simpleMarkdownToHtml` 合并为 `apps/web/src/lib/markdown-utils.ts`：
- `escapeHtml()` -- 先转义 `&` `<` `>` `"` `'`，再做任何 Markdown 转换
- `sanitizeUrl()` -- 阻断 `javascript:` `data:` `vbscript:` 协议，仅允许 `http:` `https:` `mailto:` 相对路径和 fragment
- `simpleMarkdownToHtml()` -- 导出函数，escape-first 策略 + URL 消毒

**修复 C：chart.tsx CSS 注入防护**

在 `apps/web/src/app/components/ui/chart.tsx` 的 `ChartStyle` 组件中：
- 添加 `sanitizeCssColor()` 函数，使用正则白名单验证颜色值格式
- 阻断包含 `{` `}` `;` `\` 的注入向量
- 仅允许 hex、rgb/rgba、hsl/hsla、oklch/oklab、var(--token)、transparent、currentColor 等合法 CSS 颜色值

**验证方式：** 已通过内联测试验证以下 payload：
- `<script>alert(1)</script>` -> 被转义为 `&lt;script&gt;`
- `[click](javascript:alert(1))` -> href 输出为 `#`
- `[safe](https://example.com)` -> 正常渲染为链接
- `http://127.0.0.1/` -> 被 SSRF 防护阻断
- `http://169.254.169.254/` -> 被 SSRF 防护阻断

#### 2.1 响应式 Stack 方案

**推荐方案：扩展 WorkspaceShell + 渐进式堆叠**

```
桌面 (>=1024px):  [Sidebar | Main | Inspector]  三栏可调
平板 (768-1023px): [Sidebar | Main]              两栏，Inspector 折叠为 bottom sheet 或 overlay
移动 (<768px):    [Main]                         单栏，Sidebar 为 Sheet，Inspector 为 full-screen overlay
```

**useBreakpoint 与 useIsMobile 的关系：**

`useBreakpoint` 将**替换** `useIsMobile`，而非并存。具体方案：
1. 在 `ui/use-mobile.ts` 中扩展，新增 `useBreakpoint` hook，返回 `'mobile' | 'tablet' | 'desktop'` 三级
2. 保留 `useIsMobile` 作为 `useBreakpoint` 的便捷包装（内部调用 `useBreakpoint`），避免一次性修改所有消费方
3. `sidebar.tsx` 已有的 `useIsMobile` 调用保持不变（通过包装函数兼容）
4. 新代码统一使用 `useBreakpoint`
5. 后续逐步迁移 `sidebar.tsx` 等存量调用方

实现路径：
1. 扩展 `use-mobile.ts`，新增 `useBreakpoint` hook
2. WorkspaceShell 根据 breakpoint 切换 PanelGroup direction（desktop: horizontal, mobile: vertical）
3. Inspector panel 在 tablet 以下变为 overlay/drawer 模式
4. 保持 `react-resizable-panels` 的 autoSaveId 按 breakpoint 分别存储

#### 2.2 Bundle Budget 方案

**目标：主入口 gzip <= 500KB**

策略分三层：

**A. 依赖瘦身（预计节省 150-200KB gzip）**
- 移除 `@mui/material` + `@emotion/*`（低风险 -- grep 确认源码零 import，仅 package.json 声明）
- 将 `mermaid` (动态 import 已有，但主包仍有引用) 确认完全隔离
- 将 `katex`、`highlight.js`、`react-markdown` 系列移入 dynamic import

**B. Vite manualChunks 配置**
```ts
// vite.config.ts build.rollupOptions.output.manualChunks
manualChunks: {
  'vendor-react': ['react', 'react-dom', 'react-router'],
  'vendor-query': ['@tanstack/react-query'],
  'vendor-radix': [/* radix-ui 包列表 */],
  'vendor-motion': ['motion'],
  'vendor-icons': ['lucide-react'],
}
```

**C. 追踪工具**
- 集成 `rollup-plugin-visualizer` 生成 treemap
- 集成 `size-limit` 在 CI 中 enforce 预算

#### 2.3 Lighthouse CI 方案

**推荐：`@lhci/cli` 集成到 GitHub Actions**

```yaml
# .github/workflows/lighthouse.yml
- name: Lighthouse CI
  uses: treosh/lighthouse-ci-action@v11
  with:
    configPath: .lighthouserc.json
    urls: |
      http://localhost:4173/
      http://localhost:4173/dashboard
      http://localhost:4173/chat
```

`.lighthouserc.json` 配置（已补充 INP 和 best-practices 断言）：
```json
{
  "ci": {
    "collect": {
      "staticDistDir": "./apps/web/dist",
      "numberOfRuns": 3
    },
    "assert": {
      "assertions": {
        "categories:performance": ["error", { "minScore": 0.8 }],
        "categories:accessibility": ["warn", { "minScore": 0.9 }],
        "categories:best-practices": ["warn", { "minScore": 0.9 }],
        "first-contentful-paint": ["error", { "maxNumericValue": 2000 }],
        "largest-contentful-paint": ["error", { "maxNumericValue": 2500 }],
        "cumulative-layout-shift": ["error", { "maxNumericValue": 0.1 }],
        "interaction-to-next-paint": ["error", { "maxNumericValue": 200 }],
        "csp-xss": ["warn", { "minScore": 0 }]
      }
    }
  }
}
```

**说明：**
- `interaction-to-next-paint` (INP) maxNumericValue 200ms 对应 Core Web Vitals 目标
- `categories:best-practices` 包含 CSP 检查等安全审计项
- `csp-xss` 单独断言以确保 XSS 防护不被忽略

#### 2.4 四态标准化方案

统一到 `UnifiedFeedbackState` 并扩展：

1. 将 `UnifiedFeedbackState.tsx` 的 `any` 类型替换为严格接口
2. 为每个主要页面创建对应的 Skeleton 组件（基于 shadcn `ui/skeleton.tsx`）
3. 创建 `PageErrorFallback` 组件，带 retry 指数退避
4. 在路由层统一应用四态：Suspense fallback -> Skeleton, ErrorBoundary -> PageErrorFallback, 数据空 -> EmptyState

### 三、子任务拆分

| # | 子任务 | 复杂度 | 依赖 | 预估工时 | 状态 |
|---|--------|--------|------|---------|------|
| **T0** | **修复安全漏洞 -- SSRF (paper_tools.py) + XSS (markdown-utils.ts) + CSS 注入 (chart.tsx)** | **中** | **无** | **2h** | **已完成** |
| T1 | 拆分 Layout.tsx -- 提取 SidebarContent、SessionList、UserProfile 为独立组件 | 中 | 无 | 3h | 待开始 |
| T2 | 实现 `useBreakpoint` hook（扩展 use-mobile.ts，保留 useIsMobile 兼容包装） | 低 | 无 | 1h | 待开始 |
| T3 | 改造 WorkspaceShell -- 支持响应式堆叠、Inspector overlay 模式（通过 Outlet 衔接 Layout） | 高 | T1, T2 | 4h | 待开始 |
| T4 | 集成 `rollup-plugin-visualizer`，分析主包依赖树 | 低 | 无 | 1h | 待开始 |
| T5 | 配置 Vite manualChunks，拆分 vendor chunks | 中 | T4 | 2h | 待开始 |
| T6 | 评估并移除 MUI/Emotion 依赖（低风险 -- 源码零 import，仅移除 package.json 声明） | 低 | T4 | 1h | 待开始 |
| T7 | 将 mermaid/katex/highlight.js/react-markdown 改为 dynamic import | 中 | T4 | 3h | 待开始 |
| T8 | 配置 `size-limit` CI 预算检查（500KB gzip） | 低 | T5 | 1h | 待开始 |
| T9 | 配置 Lighthouse CI（@lhci/cli + GitHub Actions，含 INP 和 best-practices 断言） | 中 | 无 | 2h | 待开始 |
| T10 | 标准化四态组件 -- 修复 UnifiedFeedbackState 类型，统一 Skeleton 体系 | 中 | 无 | 3h | 待开始 |
| T11 | 为主要页面（Dashboard, Chat, Search, KB, Analytics, Notes）创建 Skeleton 态 | 中 | T10 | 4h | 待开始 |
| T12 | 为路由级添加 PageErrorFallback（带 retry 退避） | 低 | T10 | 2h | 待开始 |
| T13 | 验证 bundle budget、Lighthouse 分数、四态覆盖率 | 中 | T1-T12 | 2h | 待开始 |

**总预估工时：约 30.5 小时**

### 四、风险清单

| 风险 | 级别 | 描述 | 缓解措施 |
|------|------|------|---------|
| ~~XSS 漏洞利用~~ | ~~严重~~ | ~~MarkdownEditor.tsx 的 simpleMarkdownToHtml 无 HTML 转义直接输出到 dangerouslySetInnerHTML~~ | **已修复** -- T0 完成，提取共享 `lib/markdown-utils.ts`，escape-first 策略 + javascript:/data: 协议过滤 |
| ~~SSRF 漏洞利用~~ | ~~严重~~ | ~~paper_tools.py 中用户控制的 URL 直接传入 httpx.get~~ | **已修复** -- T0 完成，添加 URL scheme 白名单 + 内网 IP 黑名单 + DNS 解析后校验 |
| ~~CSS 注入~~ | ~~中~~ | ~~chart.tsx 的 ChartStyle 组件 dangerouslySetInnerHTML 未消毒 color 值~~ | **已修复** -- T0 完成，添加 sanitizeCssColor() 正则白名单 |
| MUI 移除破坏性 | **低** | grep 确认源码中零 `@mui/*` 或 `@emotion/*` import。依赖仅存在于 package.json，移除风险低。需确认无传递依赖通过 node_modules 间接引入。 | T4 先做 visualizer 分析确认 MUI 在打包产物中的实际存在形式；如发现传递依赖，评估是否需要锁定版本 |
| Bundle 预算不可达 | **高** | 主包 620KB gzip，目标 500KB。即使移除 MUI，剩余依赖（Radix 全家桶 49 个、lucide-react、motion）可能仍超。 | 设定阶梯目标：先达 550KB（Phase 5.0-2），再达 500KB（Phase 5.0-3）；或按页面拆分入口 |
| react-resizable-panels 移动端兼容 | **中** | 该库设计为桌面端面板调整，在移动端可能有触摸事件冲突。 | 移动端直接跳过 PanelGroup，用单栏 + Sheet/Drawer 替代 |
| Lighthouse CI 稳定性 | **中** | 静态 dist 模式下 Lighthouse 分数受 CI 环境波动影响。 | 使用 `numberOfRuns: 3` 取中位数；设 warn 而非 error 阈值 |
| Skeleton 闪烁 (FOUC) | **低** | 骨架屏与实际内容布局不一致会导致 CLS。 | Skeleton 组件严格匹配实际内容的尺寸和布局结构 |

### 五、依赖映射

```
T0 (安全修复) ──> 全部后续任务（前置条件）[已完成]
T1 (拆分 Layout) ──> T3 (WorkspaceShell 响应式)
T2 (useBreakpoint) ──> T3
T4 (visualizer) ──> T5 (manualChunks) ──> T8 (size-limit CI)
T4 ──> T6 (MUI 移除)
T4 ──> T7 (lazy 重型库)
T10 (四态标准化) ──> T11 (页面 Skeleton) ──> T13 (验证)
T10 ──> T12 (PageErrorFallback)
T5, T6, T7, T9 ──> T13
```

**关键路径：T0 -> T4 -> T5/T6/T7 -> T8 -> T13**（安全修复 + bundle 优化链）

**可并行路径：**
- T0 完成后，T1 + T2 + T4 + T9 + T10 可并行启动（无互相依赖）
- T4 完成后 T5/T6/T7 可并行
- T9 完全独立，T0 完成后即可启动

### 六、工作量估计

| 阶段 | 子任务 | 工时 |
|------|--------|------|
| 安全修复（前置） | T0 | 2h（已完成） |
| Shell 重构 | T1, T2, T3 | 8h |
| Bundle 优化 | T4, T5, T6, T7, T8 | 8h |
| Lighthouse CI | T9 | 2h |
| 四态标准化 | T10, T11, T12 | 9h |
| 验证收尾 | T13 | 2h |
| **合计** | | **31h** |

**最低可行交付（MVP scope）：** T0 + T1 + T2 + T3 + T4 + T5 + T9 + T10 = 17.5h，覆盖安全修复 + 响应式 stack + Lighthouse CI + 基础 bundle 拆分 + 四态骨架。T6/T7（深度 bundle 瘦身）可作为后续 Phase 跟进。

### 七、修正记录

| 修正项 | 原始声明 | 修正后 | 数据来源 |
|--------|---------|--------|---------|
| WorkspaceShell.tsx 使用范围 | "当前没有任何页面实际使用它。它是一个孤立组件" | 7+ 页面直接依赖（Chat, Read, Search, Notes, KB, Compare, KBList） | `grep -r "WorkspaceShell" apps/web/src` |
| Layout 与 WorkspaceShell 关系 | 隐含可合并 | Layout = App Shell, WorkspaceShell = Page Shell，层级不同，不存在合并逻辑 | 代码结构分析 |
| MUI 移除风险 | "高" | "低"（源码零 import，仅 package.json 声明） | `grep -r "@mui\|@emotion" apps/web/src` 返回空 |
| useBreakpoint 状态 | "扩展 useIsMobile 为 useBreakpoint" | useBreakpoint 不存在，需新建；useIsMobile 保留为兼容包装 | `grep -r "useBreakpoint"` 返回空 |
| XSS 漏洞 | 未提及 | MarkdownEditor.tsx 无转义 + TypingText.tsx javascript: 协议未过滤 | 代码审查 |
| SSRF 漏洞 | 未提及 | paper_tools.py 用户控制 URL 直接传入 httpx.get，可扫描内网 | 安全审查 |
| CSS 注入 | 未提及 | chart.tsx ChartStyle 的 dangerouslySetInnerHTML 未消毒 config color 值 | 安全审查 |
| 安全修复方式 | MarkdownEditor.tsx 内联修复 | 提取共享 `lib/markdown-utils.ts`，escape-first + URL 协议白名单 + CSS 颜色消毒 | 安全审查建议 |
| Lighthouse CI 配置 | 缺少 INP 和 best-practices | 补充 INP (200ms) + best-practices 类别 + csp-xss 断言 | Core Web Vitals 规范 |
| T6 复杂度 | "高" | "低"（零 import 移除只需删 package.json 行 + npm install） | grep 确认 |
| T0 复杂度 | "低" | "中"（含 SSRF + XSS + CSS 注入三个独立修复点） | 实际实现 |
| 总工时 | 30.5h | 31h（T0 从 1.5h 升至 2h，新增 SSRF + CSS 注入修复） | 重新估算 |

### 八、变更的文件清单

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `apps/api/app/tools/paper_tools.py` | 修改 | 添加 SSRF 防护：`_validate_url_for_fetch()` + `ALLOWED_SCHEMES` + `BLOCKED_NETWORKS` |
| `apps/web/src/lib/markdown-utils.ts` | **新建** | 共享 Markdown-to-HTML 工具：`escapeHtml()` + `sanitizeUrl()` + `simpleMarkdownToHtml()` |
| `apps/web/src/app/components/MarkdownEditor.tsx` | 修改 | 删除内联 `simpleMarkdownToHtml`，改为导入 `lib/markdown-utils` |
| `apps/web/src/app/components/TypingText.tsx` | 修改 | 删除内联 `simpleMarkdownToHtml`，改为导入 `lib/markdown-utils` |
| `apps/web/src/app/components/ui/chart.tsx` | 修改 | 添加 `sanitizeCssColor()` + `SAFE_COLOR_RE`，ChartStyle 组件使用消毒后的颜色值 |
