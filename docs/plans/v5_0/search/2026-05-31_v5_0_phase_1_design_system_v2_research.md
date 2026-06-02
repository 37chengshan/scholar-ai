---
owner: web-platform
status: research-ready
last_verified_at: 2026-05-31
scope:
  - apps/web/src/styles/{theme,magazine,global,tailwind}.css
  - apps/web/src/app/components/layout/WorkspaceShell.tsx
  - apps/web/tailwind.config.js
  - apps/web/vite.config.ts
inputs:
  - 27_v5_0_overview_plan.md (Phase 5.0-1)
  - 2026-05-31_v5_0_ui_polish_and_perf_research.md
  - apps/web/src/styles/magazine.css (524 行)
  - apps/web/src/styles/theme.css (94 行, 39 vars)
  - ~/.claude/skills/pretext/SKILL.md
external_sources:
  - Material Design 3: design tokens overview (m3.material.io)
  - Shopify Polaris: token naming conventions (polaris.shopify.com/tokens)
  - GitHub Primer: 3-tier token system (primer.style/foundations/color/overview)
  - MDN: oklch() color space (developer.mozilla.org)
  - CSS-Tricks: fluid typography (css-tricks.com/snippets/css/fluid-typography/)
  - Smashing Magazine: design tokens + CSS custom properties (2024)
  - Open Design craft: typography-hierarchy-editorial.md
  - Open Design craft: anti-ai-slop.md
  - Open Design craft: color.md
  - Open Design design-systems: editorial/DESIGN.md
  - Open Design design-systems: warm-editorial/DESIGN.md
---

# 2026-05-31 Phase 5.0-1 深度研究:设计系统 v2 + 杂志编辑风深化 + 反模板视觉

> 本文是 Phase 5.0-1 (设计系统 v2) 的研究输入文档。它不替代 phase execution plan，只承载技术路线、外部对标与实现决策依据。

## 0. 用户口径

1. **保持现有杂志编辑风** — 继承 `magazine.css` 的视觉语言
2. 内页面**布局与细节都要优化** — 不只是 landing 页
3. **Chat 页面全是问题** — Chat 与杂志风严重脱节
4. 最大要求:**UI 美观 + 体验完整**

## 1. 当前杂志编辑风资产盘点

### 1.1 已就位的视觉资产 (apps/web/src/styles/)

| 资产 | 位置 | 行数 | 状态 |
|---|---|---|---|
| 暖纸 palette (#F4ECE1 / #fdfaf6 / #2d241e / #d35400) | `theme.css:2-22` | — | ✅ 品牌色已定 |
| 三栈字体 (Playfair Display + Noto Serif SC + Outfit) | `magazine.css:4` | — | ✅ Google Fonts 已 import |
| JetBrains Mono | `theme.css:35` | — | ✅ mono 栈已定 |
| Paper texture overlay (SVG noise) | `magazine.css:28-37` | — | ✅ landing 用 |
| Editorial typography hierarchy (display/heading/subtitle/body) | `magazine.css:41-57` | — | ✅ class 已定义 |
| shadow-paper (4px hard shadow, neo-brutalist) | `theme.css:42-44` | — | ✅ 已用作品牌延伸 |
| clamp() fluid font scale (--font-xs ~ --font-xl) | `theme.css:53-57` | — | ✅ 已有 |
| Sidebar/panel/rich-text 布局变量 | `theme.css:58-62` | — | ✅ 已有 |
| editorial-display / editorial-heading / ui-copy 组件类 | `theme.css:77-87` | — | ✅ 已有 |
| chat-message-list 宽度约束 | `theme.css:89-93` | — | ✅ 已有 |
| magazine.css 完整组件库 (card/section/button/input 等) | `magazine.css` | 524 | ✅ landing 用 |

### 1.2 设计 token 现状

当前 `theme.css` 的 `@theme` 块定义了 **39 个 CSS vars**:

```
颜色: ~10 个 (--color-primary/secondary/background/card/popover/muted/foreground/destructive/border/ring + chart 5 个)
字体: 5 个 (--font-serif/sans/mono/ui/editorial)
圆角: 1 个 (--radius)
阴影: 3 个 (--shadow-paper/hover/active)
```

**对比业界标杆**:
- Material Design 3: ~150 tokens (color/typography/shape/elevation/motion)
- Shopify Polaris: ~200 tokens (color alone 就有 ~60 functional tokens)
- GitHub Primer: 3-tier (base ~100 + functional ~80 + component ~40)

**结论**: 39 个 tokens 对于一个有 6 个主链页面 + 1 个 landing 的产品来说严重不足。

## 2. 外部对标:Token 架构最佳实践

### 2.1 GitHub Primer 三层 token 架构 (最值得借鉴)

| 层级 | 作用 | 示例 | 可否直接使用 |
|---|---|---|---|
| **Base** (原始值) | 最底层，映射到 raw hex/oklch | `--color-scale-orange-5` | ❌ 只作引用源 |
| **Functional** (语义层) | 全局 UI 模式 (text/border/bg/shadow) | `--bgColor-default`, `--fgColor-muted` | ✅ 主要使用层 |
| **Component** (组件层) | 特定组件的值 | `--button-primary-bg` | ✅ 只在必要时 |

**ScholarAI 应采用这个三层架构**，但命名风格适配杂志编辑风:
- Base: `--paper-50` ~ `--paper-900`, `--ink-50` ~ `--ink-900`, `--accent-50` ~ `--accent-900`
- Functional: `--color-bg`, `--color-surface`, `--color-text`, `--color-muted`, `--color-border`, `--color-accent`
- Component: `--chat-bubble-bg`, `--read-panel-border`, `--notes-editor-bg`

### 2.2 Material Design 3 的色彩语义

MD3 的色彩系统按**角色**命名而非按**值**命名:

```
primary / on-primary / primary-container / on-primary-container
secondary / on-secondary / ...
surface / on-surface / surface-variant / on-surface-variant
error / on-error / error-container
background / on-background
outline / outline-variant
```

**ScholarAI 借鉴点**: 每个颜色都有"on-"配对，确保对比度自动满足。但 MD3 的角色太多 (~30 个 color role)，对 ScholarAI 过度工程。取其精华: 保留 `on-*` 配对思路，但简化角色数量。

### 2.3 oklch 色彩空间 (MDN 已标注 Baseline Widely available)

oklch 的核心优势:
1. **感知均匀性** — 相同 L 值 = 相同亮度感知，不像 HSL
2. **色域覆盖** — 支持 P3 / Rec.2020，未来可扩展
3. **相对颜色语法** — `oklch(from var(--accent) calc(l - 0.1) c h)` 可以从一个 base color 派生暗/亮变体

**ScholarAI 应用**:
- 所有新 color token 用 oklch 定义
- 旧 hex 值保留兼容，新值不再用 hex
- 利用 relative color 语法生成 9 阶色阶 (50/100/.../900)

### 2.4 fluid typography (CSS-Tricks + 当前 theme.css)

当前 `theme.css:53-57` 已有 clamp() fluid scale:
```css
--font-xs: clamp(0.75rem, 0.72rem + 0.1vw, 0.8125rem);
--font-sm: clamp(0.8125rem, 0.78rem + 0.12vw, 0.875rem);
--font-md: clamp(0.9375rem, 0.9rem + 0.15vw, 1rem);
--font-lg: clamp(1.125rem, 1.05rem + 0.35vw, 1.25rem);
--font-xl: clamp(1.375rem, 1.2rem + 0.7vw, 1.75rem);
```

**问题**: 只有 5 级，缺 display 级 (>32px) 和 caption 级 (<12px)。
**升级方向**: 扩展到 9-10 级，覆盖 editorial display (56-96px) 和 caption (11-13px)。

## 3. 杂志编辑风内页落地策略

### 3.1 核心原则 (来自 Open Design craft: typography-hierarchy-editorial.md)

> "Editorial hierarchy means the pacing is authored the way a print art director paces a spread: entry point, tension, rest, disruption, resolution. The reader is moved through content rather than given a uniform reading surface."

**对 ScholarAI 内页的启示**:

1. **Dramatic scale jumps** — display 与 body 之间要有 3-5× 的差距，不能渐进
2. **Whitespace carries hierarchy** — 层级靠空间而非粗体标题
3. **Restrained bold** — 每 400 个 body 字最多 1-2 个粗体短语
4. **Display tracking** — 大字号必须负 tracking (-0.02em ~ -0.05em)

### 3.2 继承 vs 重做清单

**从 landing magazine.css 继承到内页**:
- ✅ Playfair Display + Noto Serif SC + Outfit 三栈
- ✅ 暖纸 palette (oklch 化后)
- ✅ shadow-paper 硬阴影 (但密度调低)
- ✅ italic / pullquote / byline 装饰类
- ✅ 微 paper-texture (密度从 0.03 降到 0.015)

**重做适配内页**:
- 🔄 字号从 display scale 改成 editorial reading scale (body 16-19px)
- 🔄 行高 1.55 → 1.65 (长文阅读优先)
- 🔄 装饰留白收一档 (内页不需要 landing 的 6rem section padding)
- 🔄 card 圆角从 1rem 改成 8px (工具感，非展示感)
- 🔄 hover 用 editorial 微位移 translateY(-1px) 而非 scale

**新增 (内页专属)**:
- ➕ Editorial pullquote — 用于 Chat 重要消息 / Read 引用 / Notes block
- ➕ Drop cap — 用于长 Chat assistant 消息开头
- ➕ Section breaks (✦ 装饰横线) — 用于 Chat / Notes / Read 长文分隔
- ➕ Margin notes — 用于 Read 页 evidence 侧栏
- ➕ Tabular numerals — 用于 Compare 矩阵 / token cost / 时间戳

### 3.3 反模板策略 (来自 Open Design craft: anti-ai-slop.md)

**ScholarAI 内页 4 个高风险模板感**:

| # | 模板感 | 来源 | 修复方案 |
|---|---|---|---|
| 1 | Card 网格统一间距 | KB list / Search results / Notes sidebar | 改 bento 不规则栅格，引入 2-3 种 card 尺寸 |
| 2 | Sidebar + content + right panel 三栏 | WorkspaceShell v1 | right panel 改为可浮出式 reading drawer |
| 3 | 统一圆角统一阴影 | 所有 card | 三档: 8px 工具卡 / 0px 阅读片 / 16px 浮层 |
| 4 | 灰白调安全色 | 全站 | 暖纸做透，hover/active 用 #d35400 accent 强调 |

**anti-ai-slop 七宗罪对照** (ScholarAI 需要检查的):

| 罪 | ScholarAI 是否犯 | 修复 |
|---|---|---|
| 1. Default Tailwind indigo | ❌ 已用 #d35400 | 无需修复 |
| 2. Two-stop trust gradient | ⚠️ 需检查 landing hero | 内页无 hero，不适用 |
| 3. Emoji as feature icons | ⚠️ README 有 emoji，内页需确认无 emoji icon | 用 Lucide mono SVG |
| 4. Sans-serif on display when serif bound | ❌ Playfair Display 已绑 display | 无需修复 |
| 5. Rounded card + colored left-border | ⚠️ 部分 card 有此 pattern | 改为 shadow-paper 硬阴影 |
| 6. Invented metrics | ❌ 无 | 无需修复 |
| 7. Filler copy | ❌ 无 | 无需修复 |

### 3.4 暗色主题策略 (来自 Open Design craft: color.md)

> "Avoid pure black and pure white — both cause vibration and eye strain."

| Token | Light | Dark |
|---|---|---|
| Background | `#fdfaf6` (暖白) | `oklch(0.14 0.01 60)` (深暖灰，非纯黑) |
| Surface | `oklch(0.99 0.005 60)` (微暖白) | `oklch(0.18 0.01 60)` |
| Text | `#2d241e` | `oklch(0.92 0.01 60)` (暖白，非纯白) |
| Muted | `#7a6b5d` | `oklch(0.60 0.01 60)` |
| Accent | `#d35400` | `oklch(0.70 0.15 50)` (明度略高，保持暖调) |
| Border | `rgba(45,36,30,0.1)` | `oklch(1 0 0 / 0.08)` (半透明白) |

**关键原则**:
- Dark theme 不是 light theme 的反色，是**独立色板**
- 保持暖调 (hue 60 = 暖黄) 而非偏冷
- 用半透明白 border 而非深色 border (来自 color.md: "prefer semi-transparent white borders over solid dark borders")
- Accent 在 dark 下明度略高 (从 oklch L 0.65 → 0.70)，确保对比度
- Dark 下覆盖同名 functional token (如 `--color-bg`)，不新建 `--dark-*` 变量 (审查 C-3 修正)
- Selector 使用 `.dark` class，对齐 next-themes / shadcn `dark:` variant (审查 C-2 修正)

## 4. Token 架构设计 (39 → ~200)

### 4.1 五大 token 族

**① Typography (~40 tokens)**

```css
/* Display (editorial, landing only) */
--font-display-xl: 4.5rem;    /* 72px */
--font-display-l: 3.5rem;     /* 56px */
--font-display-m: 2.5rem;     /* 40px */

/* Heading (内页用) */
--font-heading-1: 2rem;       /* 32px */
--font-heading-2: 1.5rem;     /* 24px */
--font-heading-3: 1.25rem;    /* 20px */
--font-heading-4: 1.125rem;   /* 18px */

/* Editorial decorative */
--font-editorial-pullquote: 1.75rem;  /* 28px, italic */
--font-editorial-byline: 0.875rem;    /* 14px, serif */
--font-editorial-deck: 1.25rem;       /* 20px, serif italic */

/* Body */
--font-body-l: 1.125rem;     /* 18px */
--font-body-m: 1rem;          /* 16px */
--font-body-s: 0.875rem;      /* 14px */

/* UI (界面元素) */
--font-ui-l: 1rem;
--font-ui-m: 0.875rem;
--font-ui-s: 0.75rem;
--font-ui-xs: 0.6875rem;     /* 11px */

/* Mono */
--font-mono-m: 0.875rem;
--font-mono-s: 0.75rem;

/* Line height */
--leading-tight: 1.2;
--leading-snug: 1.35;
--leading-normal: 1.55;
--leading-relaxed: 1.65;     /* 长文阅读 */
--leading-loose: 1.8;

/* Letter spacing */
--tracking-tighter: -0.05em;  /* display */
--tracking-tight: -0.02em;    /* heading */
--tracking-normal: 0;
--tracking-wide: 0.02em;      /* ALL CAPS */
--tracking-wider: 0.06em;     /* ALL CAPS label */

/* i18n 中文专项 */
--leading-zh-body: 1.8;       /* 中文 body 需要更松 */
--leading-zh-display: 1.3;    /* 中文 display 可以紧 */
```

**② Color (~60 tokens, oklch)**

```css
/* Base (9 阶色阶, oklch) */
--paper-50: oklch(0.98 0.01 60);   /* 最浅暖白 */
--paper-100: oklch(0.96 0.01 60);
--paper-200: oklch(0.93 0.01 60);
--paper-300: oklch(0.88 0.02 60);
--paper-400: oklch(0.80 0.02 60);
--paper-500: oklch(0.70 0.02 60);
--paper-600: oklch(0.55 0.02 60);
--paper-700: oklch(0.40 0.02 60);
--paper-800: oklch(0.25 0.01 60);
--paper-900: oklch(0.14 0.01 60);   /* 最深暖黑 */

--ink-50 ~ --ink-900;               /* 深色文字阶 */
--accent-50 ~ --accent-900;          /* #d35400 的 9 阶 */

/* Functional (语义层) */
--color-bg: var(--paper-50);
--color-surface: oklch(0.99 0.005 60); /* 卡片表面, 微暖白, 非纯白 (审查 A-1 修正) */
--color-surface-raised: ...;
--color-text: var(--ink-800);
--color-text-muted: var(--ink-500);
--color-border: oklch(0.85 0.01 60 / 0.15);
--color-accent: var(--accent-600);
--color-accent-hover: var(--accent-700);
--color-accent-text: oklch(0.45 0.15 45); /* accent darken 变体, 供正文链接用, 对比度 ≥4.5:1 (审查 A-2 修正) */
--color-on-accent: oklch(0.98 0 0);  /* accent 上的文字 */

/* Semantic */
--color-success: oklch(0.60 0.15 145);
--color-warning: oklch(0.55 0.15 80);  /* L 从 0.75 降至 0.55, 对比度 ≥3.5:1 (审查 B-1 修正) */
--color-danger: oklch(0.47 0.20 25);   /* L 从 0.55 降至 0.47, 对比度 ≥4.5:1 (审查 B-2 修正) */
--color-info: oklch(0.55 0.08 60);     /* 暖蓝替代冷蓝, 保持暖调 (审查 A-5 修正) */

/* Evidence / Verifier (学术专用, 5 种与后端 support_status 1:1 对齐, 审查 E-2 修正) */
--color-evidence-supported: oklch(0.60 0.15 145);         /* 强支持 */
--color-evidence-weakly-supported: oklch(0.65 0.12 145);  /* 弱支持 */
--color-evidence-unsupported: oklch(0.47 0.20 25);         /* 不支持 */
--color-evidence-not-enough: oklch(0.55 0.08 80);          /* 证据不足 */
--color-evidence-conflicting: oklch(0.50 0.15 300);        /* 冲突 (紫调, 区分于其他) */

/* Dark theme — 覆盖同名 functional token (审查 C-2/C-3 修正: 不新建 --dark-* 变量) */
/* 在 .dark selector 下覆盖, 对齐 next-themes / shadcn dark: variant */
/*
.dark {
  --color-bg: oklch(0.14 0.01 60);
  --color-surface: oklch(0.18 0.01 60);
  --color-text: oklch(0.92 0.01 60);
  --color-text-muted: oklch(0.60 0.01 60);
  --color-border: oklch(1 0 0 / 0.08);
  --color-accent: oklch(0.70 0.15 50);
  --color-accent-text: oklch(0.75 0.15 50);
  --color-on-accent: oklch(0.14 0.01 60);
  --color-warning: oklch(0.65 0.15 80);
  --color-danger: oklch(0.55 0.20 25);
}
*/
```

**③ Spacing (~20 tokens, fluid)**

```css
--space-1: 0.25rem;   /* 4px */
--space-2: 0.5rem;    /* 8px */
--space-3: 0.75rem;   /* 12px */
--space-4: 1rem;      /* 16px */
--space-5: 1.25rem;   /* 20px */
--space-6: 1.5rem;    /* 24px */
--space-8: 2rem;      /* 32px */
--space-10: 2.5rem;   /* 40px */
--space-12: 3rem;     /* 48px */
--space-16: 4rem;     /* 64px */
--space-20: 5rem;     /* 80px */
--space-24: 6rem;     /* 96px */
--space-32: 8rem;     /* 128px */

/* Fluid (基于编辑栏宽度) */
--space-fluid-section: clamp(3rem, 2rem + 3vw, 6rem);
--space-fluid-gutter: clamp(1rem, 0.5rem + 1.5vw, 2rem);
```

**④ Motion (~20 tokens)**

```css
/* Duration */
--duration-instant: 75ms;
--duration-fast: 150ms;
--duration-normal: 250ms;
--duration-slow: 400ms;
--duration-glacial: 800ms;

/* Easing */
--ease-standard: cubic-bezier(0.4, 0, 0.2, 1);
--ease-decelerate: cubic-bezier(0, 0, 0.2, 1);
--ease-accelerate: cubic-bezier(0.4, 0, 1, 1);
--ease-sharp: cubic-bezier(0.4, 0, 0.6, 1);
--ease-editorial: cubic-bezier(0.16, 1, 0.3, 1);  /* 编辑风优雅 */

/* Intent (语义化) */
--intent-reveal: var(--duration-normal) var(--ease-decelerate);    /* 出现 */
--intent-handoff: var(--duration-fast) var(--ease-standard);       /* 切换 */
--intent-confirm: var(--duration-instant) var(--ease-sharp);       /* 确认 */
--intent-error: var(--duration-instant) var(--ease-accelerate);    /* 错误 */
```

**⑤ Elevation (~10 tokens)**

```css
--shadow-paper: 4px 4px 0px 0px rgba(9,9,11,1);           /* 已有 */
--shadow-paper-hover: 6px 6px 0px 0px rgba(9,9,11,1);     /* 已有 */
--shadow-paper-active: 2px 2px 0px 0px rgba(9,9,11,1);    /* 已有 */
--shadow-editorial-card: 0 1px 3px oklch(0.2 0 0 / 0.06); /* 新增, 内页卡片 */
--shadow-editorial-lift: 0 4px 12px oklch(0.2 0 0 / 0.08);/* 新增, hover 提升 */
--shadow-overlay-sm: 0 2px 8px oklch(0.2 0 0 / 0.12);    /* 浮层小 */
--shadow-overlay-md: 0 4px 16px oklch(0.2 0 0 / 0.16);   /* 浮层中 */
--shadow-overlay-lg: 0 8px 32px oklch(0.2 0 0 / 0.20);   /* 浮层大 */
--shadow-focus-ring: 0 0 0 2px var(--color-accent);       /* 焦点环 */
```

### 4.2 Token 总数

| 族 | 数量 |
|---|---|
| Typography | ~40 |
| Color | ~60 |
| Spacing | ~20 |
| Motion | ~20 |
| Elevation | ~10 |
| Layout (sidebar/panel/rich-text) | ~10 |
| Border radius | ~5 |
| **总计** | **~165** |

从 39 → ~165，覆盖所有 UI 维度。

## 5. 各主链页面视觉打磨方向 (Phase 5.0-1 范围)

Phase 5.0-1 只做 **token + typography + anti-template**，不动布局。布局留给 5.0-2 ~ 5.0-6。

| 页面 | Phase 5.0-1 动作 | 不动 |
|---|---|---|
| Search | 接 token，typography 改 editorial reading scale | 不改布局 |
| KB | 接 token，card 改三档圆角 + shadow-paper | 不改网格 |
| Read | 接 token，body 改 serif (Playfair) | 不改 PDF 渲染 |
| Chat | 接 token，message body 改 serif，pullquote class | 不改 hooks/架构 |
| Notes | 接 token，editor 改 editorial font | 不改 TipTap 配置 |
| Compare | 接 token，数字改 tabular-nums | 不改矩阵布局 |
| Upload (待补) | 接 token | — |

## 6. 实现路径建议

### 6.1 文件结构 (Phase 5.0-1)

```
apps/web/src/styles/
├── tokens/
│   ├── typography.css      ← 新增, ~40 tokens
│   ├── color.css           ← 新增, ~65 tokens (oklch, 含 .dark 覆盖)
│   ├── spacing.css         ← 新增, ~20 tokens
│   ├── motion.css          ← 新增, ~20 tokens (含 prefers-reduced-motion)
│   └── elevation.css       ← 新增, ~10 tokens
├── theme.css               ← 重构, @layer base/components, 不嵌套 @import (审查 C-1 修正)
├── global.css              ← 更新, 接新 tokens
├── magazine.css            ← 更新, 内页适配 (收留白/改圆角/降密度)
└── index.css               ← 更新, @import tokens/* + theme + global + magazine (审查 C-1 修正)
```

**审查修正要点**:
- **C-1**: token 文件通过 `index.css` 的 `@import` 引入，不嵌套在 `theme.css` 的 `@theme` 块中 (CSS 规范禁止 at-rule 内嵌套 @import)
- **C-2**: dark theme 使用 `.dark` class selector (对齐 next-themes / shadcn `dark:` variant)，不使用 `[data-theme="dark"]`
- **C-3**: dark token 在 `.dark` selector 下覆盖同名 functional token (如 `--color-bg`)，不新建 `--dark-*` 变量
- **D-1**: Google Fonts 从 `@import` 迁移到 `index.html` 中的 `<link rel="preload" as="font">` + `font-display: swap`
- **D-2**: 在 `index.html` 添加 inline script 防 FOUC: 检测 `prefers-color-scheme` 并在 `<html>` 上设 `.dark` class

### 6.2 实施顺序 (调整为 3.5-4 周, 审查后修正)

1. **Week 1**: 建 `tokens/` 目录 + 写完 5 个 token 文件 (含审查修正的 CRITICAL 数值) + **font preload 迁移** + **dark FOUC script** + **dark PoC 验证**
2. **Week 2a**: UI 原语接 token (card/button/input/textarea/badge/pill)
3. **Week 2b**: feature 页面接 token (chat/read/notes/kb/search/compare) + 建 hex→token mapping 表
4. **Week 3**: dark theme 完善 + anti-template 落地 + evidence token 补齐 + motion reduced-motion 降级
5. **Week 3.5**: 回归测试 + Lighthouse 验证 + governance check

### 6.3 向后兼容

- 旧 `--color-primary` 等保留为 alias: `--color-primary: var(--accent-600);`
- 旧 `--font-serif` 等保留为 alias: `--font-serif: var(--font-editorial);`
- Tailwind 通过 `@theme` 在 `tailwind.css` 中消费 CSS vars，不改 tailwind.config.js
- `@custom-variant dark (&:where(.dark *))` 添加到 `tailwind.css` 以对齐新 selector (审查 C-2)

## 7. 风险与缓解

| 风险 | 缓解 |
|---|---|
| oklch 在旧浏览器不支持 | oklch Baseline Widely available (2023-05)，Safari 15.4+ / Chrome 111+ / Firefox 113+。用 `@supports` 降级到 hex |
| 中文 serif 渲染不一致 | i18n 中文专项 `--leading-zh-*` + `--font-weight-zh-*` token |
| magazine.css landing 与内页冲突 | 用 `.magazine-landing` scope 限 landing，内页用新 token |
| 165 tokens 过多难维护 | 三层架构 (base/functional/component) 确保大部分开发者只接触 functional 层 |
| dark theme FOUC | inline script 在 `<head>` 中检测 `prefers-color-scheme` 并同步设 `.dark` class (审查 D-2 修正) |
| dark theme 与 Tailwind 冲突 | `.dark` class selector + `@custom-variant dark (&:where(.dark *))` 对齐 shadcn (审查 C-2 修正) |
| Google Fonts @import 阻塞渲染 | 迁移到 `<link rel="preload" as="font" crossorigin>` + `font-display: swap` (审查 D-1 修正) |

## 8. 验收口径 (Phase 5.0-1 closeout)

1. ✅ tokens/ 目录 5 个文件全部落地，总计 ~165 tokens (含审查修正的 CRITICAL 数值)
2. ✅ index.css 重构为 @import tokens/*，theme.css 不嵌套 @import (审查 C-1)
3. ✅ 全站 6 主链页 + landing 的 hardcode 值替换为 token 引用 (grep 无裸 hex)
4. ✅ magazine.css 内页适配完成 (收留白/改圆角/降 paper-texture 密度)
5. ✅ `.dark` class 暗色主题可切换，无 FOUC (审查 C-2/D-2)
6. ✅ anti-template 检查: KB list / Search / Notes sidebar 无 "uniform card grid" 反例
7. ✅ npm run type-check 通过
8. ✅ 现有 vitest 全部通过 (无回归)
9. ✅ Lighthouse 主路由分数不低于当前 baseline (不因 token 改动变慢)
10. ✅ Google Fonts 已迁移到 `<link preload>` (审查 D-1)
11. ✅ evidence token 5 种与后端 support_status 1:1 对齐 (审查 E-2)
12. ✅ accent-text darken 变体对比度 ≥4.5:1 (审查 A-2)
