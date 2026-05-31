---
owner: product-engineering
status: research-ready
last_verified_at: 2026-05-31
scope:
  - apps/web/src/styles/{theme,magazine,global}.css
  - apps/web/src/features/chat/**
  - apps/web/src/features/{search,kb,read,notes,compare,uploads}/**
  - apps/web/src/app/components/layout/WorkspaceShell.tsx
  - apps/web/vite.config.ts
inputs:
  - 27_v5_0_overview_plan.md
  - 2026-05-31_v5_0_research_decision_note.md
  - 2026-05-26_v4_5_frontend_backend_multidimensional_audit.md
---

# 2026-05-31 v5.0 UI 打磨 / 性能提升 / 视觉重构研究方案

> 本文是 v5.0 在「**保持现有杂志编辑风**」前提下,对内页面 UI、视觉打磨、性能体系与 Chat 页面集中重构的研究方案。它是 phase 5.0-1、5.0-2、5.0-6 的输入文档,不替代 phase execution plan。

## 0. 用户口径(必须满足)

1. **保持现有杂志编辑风**(`magazine.css` + `Playfair Display + Noto Serif SC + Outfit` 三栈不动)
2. 内页面**布局与细节都要优化**
3. **Chat 页面现在全是问题** — 集中精修
4. 同时提升**性能**
5. 最大要求:**UI 美观 + 体验完整**

## 1. 当前杂志编辑风资产盘点(继承基础)

### 1.1 已就位的视觉资产

| 资产 | 位置 | 状态 |
|---|---|---|
| Playfair Display + Noto Serif SC + Outfit 三栈 | `apps/web/src/styles/magazine.css:4` | ✅ Google Fonts 已 import |
| 暖色纸感 palette (#F4ECE1 / #fdfaf6 / #2d241e / #d35400) | `theme.css:2-22` | ✅ 已用作 brand color |
| Paper texture overlay (SVG noise) | `magazine.css:28-37` | ✅ 已用于 landing |
| Editorial typography hierarchy (display/heading/subtitle/body) | `magazine.css:41-57` | ✅ 已定义 class |
| shadow-paper (4px hard shadow) | `theme.css:42-44` | ✅ neo-brutalist 风格延伸 |
| 39 个 CSS vars 起点 | `theme.css` | ⚠️ 数量过少 |
| `editorial-display` / `editorial-heading` / `chat-message-list` 组件类 | `theme.css:77-93` | ✅ 已有但不完整 |

### 1.2 杂志风评分(现状)

- **Landing 页:9/10** — magazine.css 已完整应用,视觉编辑感强
- **主链 6 页:4/10** — 字体已对接但布局规则未做编辑化,大量 `card grid + uniform spacing` 模板感
- **Chat 页:3/10** — 与杂志风严重脱节,工业感强

**这就是为什么"Chat 全是问题"的视觉根源**。

## 2. Chat 页面问题全盘点(用户最痛点)

### 2.1 架构问题

| # | 问题 | 证据 |
|---|---|---|
| C-1 | **主入口已冻结但仍在用** | `ChatWorkspaceV2.tsx:1-24` 明确写 "LEGACY FREEZE (PR10) ... in migration mode. Do not add new business logic here" |
| C-2 | **状态极度分散** | 24 个 hooks + 4 个 orchestration hooks (`useChatSessionOrchestration` / `useChatSessionBinding` / `useChatStreamingSync` / `useChatWorkspaceViewState`),逻辑难追 |
| C-3 | **本地 useState 与 store 双源** | `ChatWorkspaceV2.tsx:57-67` 同时用 `useState(sending)` + `useState(sessionTokens)` + `useState(sessionCost)` + `useState(forceNewSessionForNextSend)` + `useState(sessionSearchQuery)` 以及 `useChatWorkspace()` store,职责分裂 |
| C-4 | **HARD RULES 注释未沉淀为 type** | `ChatWorkspaceV2.tsx:20-23` HARD RULE 0.2 / 0.3 / 0.4 仅以注释形式存在 |

### 2.2 视觉/布局问题

| # | 问题 | 影响 |
|---|---|---|
| C-5 | **杂志编辑风完全没下沉到 Chat** | message bubble / composer / sidebar 走通用工业组件,与 landing 风格断裂 |
| C-6 | **8 个子组件目录视觉不统一** | `citation-panel` / `evidence` / `reasoning-panel` / `tool-timeline` / `workbench` / `composer-input` / `message-feed` / `session-sidebar` 各自为政,无设计契约 |
| C-7 | **响应式断裂** | P1-FE-004 已修但 Chat 三栏 (sidebar + feed + right panel) 在窄屏可读性仍差 |
| C-8 | **typography 未编辑化** | message body 用 sans,丧失"在读一篇被分发的学术对话"的杂志气质 |

### 2.3 交互/体验问题

| # | 问题 | 影响 |
|---|---|---|
| C-9 | **SSE 期间 layout shift** | P1-FE-001 已部分修(trace_id 透传)但 message 高度仍随流式抖动 |
| C-10 | **virtualization 缺失** | 长会话渲染全部 DOM,性能差 |
| C-11 | **键盘流不完整** | 24 hooks 没看到统一 keyboard shortcut hook |
| C-12 | **citation 跳转 UX 弱** | EvidenceBlockCard 已存在但 hover / preview / 锚定笔记 链路不完整 |
| C-13 | **Chat↔Notes 集成几乎为零** | `useEvidenceNavigation` / `chatHandoff` 单向引用 Notes,反向几乎没有 |
| C-14 | **reasoning panel / tool timeline 状态语义混乱** | partial / degraded / corrective / fallback / recovery 在后端已统一(phase6_runtime),前端没有视觉对应 |
| C-15 | **composer 输入体验弱** | 单行 / 无 @ mention / 无快捷键 / 无多模态预览 |
| C-16 | **session sidebar 信息密度低** | 仅显示标题与时间,缺少 paper scope / token cost / verdict 状态 |

### 2.4 Chat 重构 vs 精修决策

**结论:精修 + 解冻 + 集成桥,不重写**

- 重写代价:7141 行 + 25 test + 24 hooks → 至少 8-12 周 + 高回归风险
- 精修代价:把 ChatWorkspaceV2 解冻 + 子目录视觉重做 + 集成桥 → 2-3 周(phase 5.0-6 范围)
- 关键动作:
  1. 把 `LEGACY FREEZE` 注释明确取消,新规则写进 architecture doc
  2. 把 24 个 hooks 收敛为 ~10 个 (分:session / streaming / scope / runtime / handoff / keyboard / orchestration)
  3. 把 8 个子组件目录纳入统一 design contract
  4. 增加 message virtualization (用 pretext 高度预测)
  5. 增加 Chat↔Notes 双向集成

## 3. 杂志编辑风设计系统 v2 (Phase 5.0-1 输入)

### 3.1 token 扩展路线 (39 → ~200)

```css
/* 当前 39 个 vars,集中在 color + font 基础 */
/* v5.0 扩展为以下五大族: */

/* ① typography (从 6 扩到 ~40) */
--font-display-xl, --font-display-l, --font-display-m
--font-heading-1, --font-heading-2, --font-heading-3, --font-heading-4
--font-editorial-pullquote, --font-editorial-byline, --font-editorial-deck
--font-body-l, --font-body-m, --font-body-s
--font-ui-l, --font-ui-m, --font-ui-s, --font-ui-xs
--font-mono-m, --font-mono-s
--leading-tight, --leading-snug, --leading-normal, --leading-relaxed, --leading-loose
--tracking-tighter, --tracking-tight, --tracking-normal, --tracking-wide, --tracking-wider
/* + i18n 中文专项 (中文 body 需要更松 leading) */
--leading-zh-body, --leading-zh-display

/* ② color (从 ~10 扩到 ~60) */
/* 改用 oklch + semantic */
--color-paper-50/100/200/300/400/500/600/700/800/900
--color-ink-50/100/.../900     /* dark text scale */
--color-accent-50/.../900      /* d35400 加深为 9 阶 */
--color-evidence-50/.../900    /* 引用 / verifier 用色 */
--color-state-success/warning/danger/info (各 3 阶)
/* dark theme 独立色板,非反色 */
--color-dark-paper-50/.../900

/* ③ spacing (从 0 扩到 ~20) */
/* 改用 fluid clamp,基于编辑栏宽度 */
--space-1/2/3/4/5/6/8/10/12/16/20/24/32/40/48/64
--space-fluid-section, --space-fluid-gutter

/* ④ motion (从 0 扩到 ~20) */
--duration-instant/fast/normal/slow/glacial
--ease-standard/decelerate/accelerate/sharp/editorial
--intent-reveal, --intent-handoff, --intent-confirm, --intent-error

/* ⑤ elevation (从 3 扩到 ~10) */
--shadow-paper, --shadow-paper-hover, --shadow-paper-active   /* 已有 */
--shadow-editorial-card, --shadow-editorial-lift
--shadow-overlay-sm/m/l
--shadow-focus-ring
```

### 3.2 杂志风内页面落地原则

不要把 landing 的 magazine.css 简单照搬到内页;内页是**编辑工具**,不是**编辑封面**。

**继承的(从 landing 拿过来):**
- ✅ Playfair Display + Noto Serif SC + Outfit 三栈
- ✅ 暖纸 palette
- ✅ shadow-paper 硬阴影
- ✅ italic / pullquote / byline 装饰类
- ✅ 微 paper-texture 在大背景(密度调低到 0.015)

**重做的(适配内页工作场景):**
- 🔄 字号尺度从 display 改成 editorial reading scale (16-19px body)
- 🔄 行高 1.6 → 1.65 (长文阅读优先)
- 🔄 装饰留白尺度收一档 (内页不需要 landing 的 6rem section padding)
- 🔄 paper-texture 强度调低
- 🔄 card 不用大圆角,用 8px + shadow-paper 硬阴影维持编辑感
- 🔄 hover 状态用 editorial 微位移 (translateY(-1px)) 而非常见 scale

**新增的:**
- ➕ Editorial pullquote 用于 Chat 重要消息 / Read 引用 / Notes block
- ➕ 列号 / 段标记 / 边栏注 (margin notes) 用于 Read 与 Notes
- ➕ Drop cap 用于长 chat assistant 消息开头
- ➕ Section breaks (✦ 或装饰横线) 用于 Chat / Notes / Read 长文分隔
- ➕ Tabular numerals 用于 Compare 矩阵 / token cost / 时间戳

### 3.3 反模板风险防御

ScholarAI 当前内页有四个高风险模板感:

1. ⚠️ **Card 网格统一间距** (KB list / Search results / Notes sidebar) → 改 bento 不规则栅格
2. ⚠️ **Sidebar + content + right panel 三栏** → 把 right panel 改为可浮出式 reading drawer (而非永久占栏)
3. ⚠️ **统一圆角统一阴影** → editorial 用三档:8px 工具卡 + 0 px 阅读片 + 16px 浮层
4. ⚠️ **灰白调安全色** → 把暖纸做透,在 hover/active 用 #d35400 accent 强调

## 4. 内页 UI 打磨方向(主链 6 页 + Upload)

### 4.1 主链 7 页打磨清单

| 页 | 当前问题 | v5.0 视觉/布局优化方向 | 所属 phase |
|---|---|---|---|
| **Search** | 结果卡 grid + uniform spacing 模板感重;source 切换 chip 不显眼 | bento 网格、source 顶部 ribbon、active source 编辑式高亮、引用图谱 hover card | 5.0-1 + 5.0-2 |
| **KB** | 论文卡密度低 / 状态色不明显 / 搜索 result fallback 不明显 | 论文 ribbon 状态、metadata 编辑式 byline、ready/processing/failed 用 editorial state pill | 5.0-1 + 5.0-2 |
| **Read** | PDF 与右侧 evidence + notes 三栏在长文阅读时拥挤;annotation hover 弱 | pretext 接入 evidence 侧栏 + 笔记浮排;PDF 主区扩宽;margin notes 出现;reading progress 顶部细条 | 5.0-4 |
| **Notes** | editor 工业感 / 引用嵌入弱 / sidebar 信息少 | block-based editor + atomic mention pill + pretext 多栏排版 + drop cap + pullquote | 5.0-5 |
| **Chat** | 见第 2 节 16 项问题 | 见第 5 节集中方案 | 5.0-6 |
| **Compare** | 矩阵密度高但视觉无对齐感 / 0 test | tabular numerals + editorial 边框 + 列头 sticky + heat map(可选) + 补 E2E | 5.0-6 + 5.0-9 |
| **Upload (新)** | 页路由不存在 | 拖拽中央区 + 阶段进度卡 + 失败重试按编辑稿件状态色;接 SSE 实时进度 | 5.0-3 |

### 4.2 WorkspaceShell v2 (Phase 5.0-2)

**当前 (v1) 已落地:**
- 横向 PanelGroup
- Search 增加 `md:min-w-[500px]`
- P1-FE-004 已修

**v2 升级方向:**
1. 响应式 stacking (< 1024px 切单栏 + drawer; < 768px 切移动布局)
2. 密度系统 (`compact` / `comfortable` / `spacious` 三档,持久化)
3. 顶部"读者面包屑"(editorial breadcrumb,显示 paper > section > chunk)
4. 全局 Cmd+K command palette (跳转 / 搜索 / 笔记)
5. 全局键盘 cheatsheet (按 ?)

## 5. Chat 页集中重构方案 (Phase 5.0-6 输入)

### 5.1 解冻 + 收敛(架构层)

1. 把 `ChatWorkspaceV2.tsx:1-24` 的 LEGACY FREEZE 注释明确取消,改写为 v5.0 的 ownership 注释
2. 把 24 hooks 收敛为 9-10 个职责清晰的 hook:
   - `useChatSession` (创建/加载/切换/删除)
   - `useChatStream` (SSE + retry + cancel)
   - `useChatScope` (paper / KB / compare)
   - `useChatHandoff` (从 Read/KB/Search 跳入)
   - `useChatKeyboard` (新)
   - `useChatNotesBridge` (新, 双向集成)
   - `useChatViewState` (UI 局部)
   - `useChatRuntime` (phase6_runtime 字段)
   - `useChatVirtualization` (新, 用 pretext 高度)
   - `useChatTelemetry` (token cost / latency)
3. 把 HARD RULE 0.2 / 0.3 / 0.4 沉淀为 TypeScript discriminated union 类型
4. 取消 ChatWorkspaceV2 的 5 个本地 useState,全部进 workspace store 或 derived selector

### 5.2 视觉重做 (8 子组件目录)

每个子目录都要拿到 design contract:

| 子目录 | 视觉契约 | 杂志编辑风落地点 |
|---|---|---|
| `message-feed` | virtualization + drop cap + section break | 长文阅读编辑感 |
| `composer-input` | 编辑桌面感、editorial border、`/` slash menu | 编辑工具语言 |
| `session-sidebar` | 期刊目录式列表、scope ribbon、token byline | 期刊 TOC 隐喻 |
| `citation-panel` | margin note + pullquote | 学术注释隐喻 |
| `evidence` | editorial card + paper byline + source ribbon | 引用稿件隐喻 |
| `reasoning-panel` | sealed editorial draft + auto-collapse | 编辑底稿隐喻 |
| `tool-timeline` | editorial timeline + state pill | 排版进度隐喻 |
| `workbench` | sticky editor sidebar + 任务卡 | 编辑工作台隐喻 |

### 5.3 关键交互优化

1. message virtualization (用 pretext `prepare()` + `layout()` 预测高度,消除 SSE layout shift)
2. composer 升级:多行、@ mention paper/note/session、`/cmd` slash menu、Cmd+Enter 发送
3. citation hover preview (Radix `HoverCard` 已在依赖)
4. evidence → 笔记一键引用 (新建笔记 / 追加到指定笔记)
5. reasoning panel 自动折叠到 60% 透明
6. tool timeline 把 phase6_runtime 字段做语义可视化(degraded/corrective/fallback/recovery 四档色 + 图标)
7. compare card 重做(tabular numerals + heat map 可选)
8. SSE retry / cancel 两个动作做 editorial state announce(不只是 toast)

### 5.4 Chat↔Notes 集成桥

```
Chat 内:
  - @ mention 笔记 (atomic pill)
  - 引用笔记片段 (block embed)
  - 一键 "Push to note" (新建 / 追加)
  - 当前 session 自动出现在 sidebar "linked notes"

Notes 内:
  - @ mention chat session (atomic pill)
  - 引用 chat assistant 输出 (block embed)
  - "Continue in chat" 按钮 (用当前段落作 system prompt)
  - reverse link 自动维护
```

后端需要补的 API(Phase 5.0-7):
- `POST /api/v1/notes/:id/append-from-chat` (用 chat answer + citation 追加)
- `POST /api/v1/chat/sessions/:id/link-note` (双向链)
- `GET /api/v1/chat/sessions/:id/linked-notes`
- `GET /api/v1/notes/:id/linked-sessions`

## 6. 性能体系 (Phase 5.0-2 输入)

### 6.1 现状基线

| 项 | 当前 |
|---|---|
| Vite manualChunks | ❌ 未配 |
| rollup-plugin-visualizer | ❌ 未装 |
| Lighthouse CI | ❌ 未接 |
| Bundle budget | ❌ 无 |
| Route-level preload | ❌ 无 |
| Image lazy | ⚠️ 未统一 |
| Font preload | ❌ 仅 Google Fonts @import (运行时阻塞) |
| Code split | ⚠️ 仅 routes lazy |

### 6.2 v5.0 性能基线建立(Phase 5.0-2)

```ts
// apps/web/vite.config.ts 升级方向
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    visualizer({ filename: 'dist/stats.html', gzipSize: true, brotliSize: true }),
  ],
  build: {
    sourcemap: true,
    chunkSizeWarningLimit: 200, // 200 KB gzipped warning
    rollupOptions: {
      output: {
        manualChunks: {
          // 按 feature 分包
          'feature-chat': ['@/features/chat'],
          'feature-read': ['@/features/read', 'pdfjs-dist', 'react-pdf'],
          'feature-notes': ['@/features/notes', '@tiptap/react', '@tiptap/starter-kit'],
          'feature-kb': ['@/features/kb'],
          'feature-search': ['@/features/search'],
          'feature-compare': ['@/features/compare'],
          'feature-uploads': ['@/features/uploads'],
          // 大库独立
          'vendor-pdf': ['pdfjs-dist', 'react-pdf'],
          'vendor-tiptap': ['@tiptap/react', '@tiptap/starter-kit', '@tiptap/suggestion'],
          'vendor-radix': [/* @radix-ui/* */],
          'vendor-motion': ['motion'],
          'vendor-pretext': ['@chenglou/pretext'],  // 新增
        },
      },
    },
  },
})
```

### 6.3 Bundle budget (v5.0-2 落定 + 5.0-9 验收)

| 包 | 目标 (gzipped) |
|---|---|
| 首屏 (`index.html` + critical CSS + entry chunk) | ≤ 80 KB |
| `vendor-react` | ≤ 60 KB |
| `vendor-radix` | ≤ 50 KB |
| `vendor-pdf` | ≤ 200 KB (用 dynamic import 隔到 Read 页) |
| `vendor-tiptap` | ≤ 80 KB (隔到 Notes 页) |
| `feature-*` 单包 | ≤ 80 KB |
| 总下载 (首屏 + 4 个主链路由) | ≤ 500 KB |

### 6.4 Core Web Vitals 目标 (v5.0-9 release-pass 必要条件)

| 指标 | 目标 (主路由) |
|---|---|
| LCP | < 2.5 s |
| INP | < 200 ms |
| CLS | < 0.05 (Chat 期间 SSE 也必须不掉) |
| FCP | < 1.5 s |
| TBT | < 200 ms |

### 6.5 Font loading

```html
<!-- 把 magazine.css 的 @import 改为 link rel=preload + font-display: swap -->
<link rel="preload" href="..." as="font" type="font/woff2" crossorigin>
```

实测预期:消除 magazine.css `@import` 引起的 ~300ms render-blocking。

### 6.6 PDF / TipTap 动态加载

```ts
// Read 页:pdfjs-dist + react-pdf 改 dynamic import,首次进入再加载
const { Document } = await import('react-pdf');

// Notes 页:TipTap extensions 按需加载
const codeBlock = await import('@tiptap/extension-code-block');
```

### 6.7 Image / 图标策略

- Lucide React 改 `lucide-react/dist/esm/icons/X.js` 树摇 (已默认,但要确认 ESM build)
- 任何 raster image 配 explicit width/height + lazy
- avatars / paper thumb 用 sharp 端 webp/avif

### 6.8 Motion / Animation 预算

- 主链动画只允许 `transform` + `opacity`
- `will-change` 必须用完即清
- 任何 keyframe 必须能在 `prefers-reduced-motion` 下降级 (Read/Notes/Chat 已部分支持)

## 7. 推荐落地顺序

```
Phase 5.0-1 (2-3 周)
  Week 1: token 扩展 + 杂志风内页适配 + magazine.css 重构为 design system v2
  Week 2: 7 主链页 typography + spacing 全部接 token
  Week 3: anti-template 视觉策略落到 KB list / Search / Compare 三页

Phase 5.0-2 (2-3 周)
  Week 1: Vite 配置 + visualizer + manualChunks + bundle budget
  Week 2: Lighthouse CI + 路由 preload + font preload
  Week 3: WorkspaceShell v2 + 密度系统 + Cmd+K command palette

Phase 5.0-3 (上传可视化) — 视觉接入 5.0-1 token
Phase 5.0-4 (Read + pretext) — 视觉接入 5.0-1 + 性能接入 5.0-2
Phase 5.0-5 (Notes + editorial 排版) — 视觉接入 5.0-1 + 性能接入 5.0-2
Phase 5.0-6 (Chat 解冻 + 集成桥) — 全部继承上游 phase
Phase 5.0-7 / 5.0-8 — 后端
Phase 5.0-9 — Lighthouse / CLS / Bundle / E2E gate 全验收
```

## 8. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 杂志编辑风过度装饰拖累工作效率 | 内页装饰用"低频出现 + 高密度信息共存"原则,装饰只用于 reading / heading / quote |
| 内页 italic / serif 中文渲染不一致 | i18n 中文专项 `--leading-zh-*` + `--font-weight-zh-*` token,在 Phase 5.0-1 收口 |
| pdfjs-dist 200KB 影响首屏 | 用 dynamic import 隔到 Read 页 |
| TipTap 多 extension 累积体积 | 按需加载 + tree-shake |
| Chat 解冻后回归测试压力 | Phase 5.0-6 必须保留 25 个现有 test 全过,再补 ~10 个新 test |
| pretext 接入引入新依赖 | 在 Phase 5.0-1 完成 thin adapter,集中评估 |
| 性能 budget 与"杂志编辑风"装饰冲突 | 装饰用 CSS / SVG inline,绝不引图;font-display swap |

## 9. 验收口径 (release-pass 子项)

1. ✅ 杂志编辑风内页应用率 ≥ 80% (token / typography / spacing / shadow 全部接 v2)
2. ✅ 反模板检查:KB list / Search / Notes sidebar 无 "uniform card grid" 反例
3. ✅ Chat 解冻完成:`LEGACY FREEZE` 注释取消,hooks 收敛到 ≤ 10 个
4. ✅ Chat↔Notes 双向集成桥可用 (4 个 API + UI 流程)
5. ✅ Lighthouse 主路由 ≥ 90,CLS < 0.05
6. ✅ Bundle 首屏 ≤ 500 KB gzipped
7. ✅ Read / Notes / Chat / KB 全部支持 reduced-motion
8. ✅ Cmd+K command palette 可达 ≥ 80% 高频操作
9. ✅ 上传可视化 7 阶段 (upload→parse→chunk→embed→index→ready→linked) 全部可视
10. ✅ Compare / Read 补满 E2E + component test
