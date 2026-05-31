# Phase 5.0-1 审查报告: 维度 A — 设计视觉

**审查人**: design-visual-reviewer
**审查对象**: `docs/plans/v5_0/search/2026-05-31_v5_0_phase_1_design_system_v2_research.md`
**日期**: 2026-05-31

---

## Executive Verdict

**PASS-WITH-WARNINGS**

研究文档整体设计水准扎实。三层 token 架构借鉴 GitHub Primer 是正确决策，oklch 色彩空间升级、杂志编辑风内页适配策略、anti-template 四点修复方向都具备专业判断力。但存在两个必须在执行前修正的高风险问题：(1) `--color-surface: oklch(1 0 0)` 纯白直接违反 color.md「避免 pure white」的核心原则；(2) accent `#d35400` 在纯白背景上对比度仅约 2.89:1，不满足 WCAG AA body text 4.5:1 最低要求，需要为正文使用场景定义 darken 变体。此外 tracking token 已定义但未建立「哪级字号用哪档 tracking」的显式映射，暗色主题 accent chroma 偏高需确认在深色底上的可读性。

---

## Findings

| # | 严重度 | 位置 | 问题 | 建议修复 |
|---|---|---|---|---|
| A-1 | **CRITICAL** | §4.1 ② Color / `--color-surface` | `--color-surface: oklch(1 0 0)` 是纯白，直接违反 color.md 核心规则「Avoid pure black and pure white — both cause vibration and eye strain」以及 warm-editorial DESIGN.md「Never use pure black or pure white anywhere user-facing」。当前 `theme.css` 的 `#ffffff` 同样有此问题，但 v2 研究文档是修正的契机，不应继承错误。 | 改为 `--color-surface: oklch(0.99 0.005 90)` 或 `#fefcf9`（极淡暖白，肉眼感知接近白但避免 pure white vibration）。对齐 warm-editorial 的 `#FFFFFF` → 也应改为 `#FAF7F2` 级别的 surface 或用 `paper-50` 变体。 |
| A-2 | **CRITICAL** | §4.1 ② Color / accent 对比度 | `#d35400` (oklch ≈ L 0.65 C 0.17 H 45) 在纯白背景上的对比度约 **2.89:1**，不满足 WCAG AA body text (≤16px) 的 4.5:1 要求。研究文档定义了 `--color-accent: var(--accent-600)` 但未定义 `accent-600` 的具体 oklch 值，也没有区分 fill-use 和 text-use 两种场景。 | 1) 定义 `--accent-600` 时确保 L 值 ≤ 0.55 以达到 4.5:1（如 `oklch(0.55 0.17 45)` ≈ #b54600）。2) 保留当前高明度 accent 仅用于 fills（按钮背景、badge 背景），text-use 走 darken 变体。3) 在 token 注释中标注 contrast pairing 场景。 |
| A-3 | **HIGH** | §4.1 ① Typography / tracking | research 定义了 `--tracking-tighter: -0.05em` 到 `--tracking-wider: 0.06em` 五档 tracking token，但**未建立 level → tracking 的显式映射表**。editorial craft 要求 display 56px+ 必须 `-0.02em ~ -0.05em`、ALL CAPS label 需 `0.06em ~ 0.1em`，目前这些对应关系只存在于 prose 描述中，实现者可能遗漏。 | 在 typography.css 中为每级字号追加注释或通过组合 token 如 `--tracking-display: var(--tracking-tighter)` 显式绑定。或在 §3.1 的「editorial hierarchy principles」下新增一张 level → (size, weight, tracking, leading) 的完整映射表，类似 editorial craft 的 §hierarchy table。 |
| A-4 | **HIGH** | §4.1 ① Typography / heading weight | 现有 `global.css:194` 对 editorial-reading-surface headings 使用 `font-weight: 600`。editorial craft §3「Restrained bold」明确规定「editorial display is often set in light or regular weight — hierarchy is carried by scale and space, not mass」，且 §anti-patterns 首条即「Bold display headline — editorial display is usually light or regular」。research 文档未指出现有 weight-600 需要调整。 | 明确规定 H1/H2 display 级 heading 用 `font-weight: 400` (regular) 或 `300` (light)；H3/H4 可保留 `500`。bold 仅用于 body 内强调，不用于 section headings。在 typography token 中加入 `--weight-display: 400` 和 `--weight-heading: 500`。 |
| A-5 | **HIGH** | §3.4 暗色主题 / accent | 暗色主题 accent `oklch(0.70 0.15 50)` — L=0.70 C=0.15 是高饱和中亮度。在 `oklch(0.14 0.01 60)` 深色底上，这个 chroma 可能产生光晕效应 (chromatic vibration)，尤其在小字号 (14px) 正文中。color.md 要求 dark surface 上 accent 应调整到可用对比度。 | 1) 在暗色主题中降低 chroma 至 `C ≤ 0.10`（如 `oklch(0.72 0.10 50)`），保持暖调但减少光晕。2) 验证正文字号 (14-16px) 下与暗色背景的实际对比度 ≥ 4.5:1。3) 可考虑在 dark.css 中为 accent 定义 `--dark-accent-fill` (高 chroma 用于按钮填充) 和 `--dark-accent-text` (低 chroma 用于文字)。 |
| A-6 | **MEDIUM** | §3.3 anti-template / emoji | 研究将 ✦ 装饰横线列为新增 section break 元素。但 anti-ai-slop 罪 #3 明确禁止「Emoji as feature icons inside h*, button, li, or class*="icon"」。虽然 ✦ 不在 linter 的 emoji 列表中，但使用 Unicode 装饰符号作为结构性 UI 元素边界模糊。 | 1) section break 改用 SVG dingbat (monoline, 1.6-1.8px stroke, currentColor)，如 typographic ornament SVG。2) 若坚持用 ✦，确保它仅出现在 CSS `::before`/`::after` 伪元素中，不进入 JSX markup，避免 DOM 语义污染。 |
| A-7 | **MEDIUM** | §4.1 ② Color / `--color-surface-raised` | `--color-surface-raised` 值为 `...`（省略号占位），执行时如果未及时填充，可能导致开发者临时硬编码白色或灰色。 | 在 research 阶段就定义具体值，如 `oklch(0.985 0.005 90)`（比 surface 亮一档），或用 `color-mix(in srgb, var(--color-surface) 95%, var(--color-bg))` 派生。 |
| A-8 | **MEDIUM** | §4.1 ② Color / --color-info | `--color-info: oklch(0.60 0.10 240)` 的 hue 240 是冷蓝。在暖纸编辑风中，冷蓝色 info 色会破坏整体暖调一致性。warm-editorial DESIGN.md 的 forest accent `#2F5B4F` (hue ≈ 160) 比纯蓝更合适。 | 将 info 色 hue 调向暖蓝绿区间，如 `oklch(0.60 0.10 195)` (teal) 或 `oklch(0.60 0.08 210)` (muted blue)。确保不会与 success (hue 145) 混淆。 |
| A-9 | **MEDIUM** | §4.1 ④ Motion / `--ease-editorial` | `--ease-editorial: cubic-bezier(0.16, 1, 0.3, 1)` 是 ease-out-expo 函数，适合 entrance animation 但不适合 exit。research 没有为 editorial 退出/消失定义对应的 easing。 | 增加 `--ease-editorial-exit: cubic-bezier(0.7, 0, 0.84, 0)` 用于 editorial 元素的退场。或在 intent 语义中区分 reveal (enter) 和 dismiss (exit)。 |
| A-10 | **LOW** | §3.2 继承清单 | 现有 `magazine.css:79` `.magazine-card` 圆角 `1rem`，research 说改 8px 工具卡。但 `theme.css:40` 的 `--radius: 0.625rem` (10px) 是全局默认。三档圆角方案 (8px / 0px / 16px) 与全局 `--radius` 关系未说明。 | 在 spacing/elevation tokens 中明确 `--radius-tool: 0.5rem` (8px)、`--radius-reading: 0`、`--radius-float: 1rem` (16px)，并将 `--radius` alias 指向 `--radius-tool` 作为默认。 |
| A-11 | **LOW** | §4.2 Token 总数 | research 预估 ~165 tokens 但 color 章节示例中 `--ink-50 ~ --ink-900` 和 `--accent-50 ~ --accent-900` 用省略号跳过，实际仅列出了 paper 阶 + 部分 functional + semantic。ink 和 accent 的 9 阶色阶具体 oklch 值未给出，估算可能偏低。 | 补全 ink-50/100/.../900 和 accent-50/100/.../900 的 oklch 值（可用 relative color syntax `oklch(from var(--color-foreground) ...)` 派生），重新核实总 token 数。 |
| A-12 | **LOW** | 全局 | research 引用了 warm-editorial DESIGN.md 但未引用其关键约束「One accent color per screen. If a page has a terracotta hero, secondary CTAs are foreground-only, not forest」。在 §3.3 anti-template 中提到了 `#d35400` accent，但未提及是否引入 secondary accent `#2F5B4F` (forest)。 | 明确声明 ScholarAI 的 accent discipline：主 accent = terracotta (#d35400)，次 accent = forest (#2F5B4f) 仅用于 tags/dividers，不在同一 screen 上与 terracotta 同时作为 CTA。符合 color.md「at most 2 visible uses of --accent per screen」。 |

---

## 正面发现

1. **三层 token 架构选型精准** — 借鉴 GitHub Primer 的 base/functional/component 三层，命名适配杂志编辑风（paper/ink/accent），既专业又不照搬。base 层仅供引用、开发者只接触 functional 层的设计决策大幅降低维护成本。

2. **oklch 色彩空间升级有远见** — 利用 oklch 感知均匀性和 relative color syntax 派生 9 阶色阶，比 HSL 更科学。对 oklch 浏览器支持的 `@supports` 降级策略也是必要的安全网。

3. **内页适配策略判断准确** — 正确识别了 landing→内页的 5 个关键差异（字号/行高/留白/圆角/hover 行为），每项都有具体数值而非模糊方向。paper-texture 密度从 0.03 降到 0.015 是细腻的密度控制。

4. **中文排版 token 前瞻** — `--leading-zh-body: 1.8` 和 `--leading-zh-display: 1.3` 的中文专项变量展示了对 CJK 排版差异的理解，这在同类研究中少见。

5. **anti-template 四点修复精准** — 每个模板感问题都有具体来源定位（KB list / WorkspaceShell / 所有 card / 全站）和明确修复方案（bento 栅格 / reading drawer / 三档圆角 / 暖纸透），不是泛泛而谈。

6. **motion token 语义化** — `--intent-reveal/handoff/confirm/error` 将 motion 定义为意图而非时长+缓动的机械组合，这是 Material Motion 的精华。`--ease-editorial` 专用缓动函数体现了品牌一致性的关注。

7. **向后兼容设计周全** — 旧 `--color-primary` → `var(--accent-600)` 的 alias 策略确保迁移不断裂。Tailwind `@theme` 无需改 config 的兼容路径减少了实施阻力。

8. **shadow-paper 硬阴影的品牌延续** — 保留 4px hard shadow (neo-brutalist) 作为品牌资产，同时为内页新增柔和的 `--shadow-editorial-card`，区分 landing 活力和内页沉稳，是成熟的视觉分层。

---

## 与 Open Design craft 的对齐检查

### typography-hierarchy-editorial.md

| Craft 要求 | Research 对齐 | 状态 |
|---|---|---|
| Dramatic scale jumps (3-5× display/body gap) | 定义了 display-xl 72px → body-m 16px = 4.5× gap | ✅ 完全对齐 |
| Whitespace carries hierarchy | 内页适配明确收留白 (6rem → ~3rem)，但保留 whitespace-as-hierarchy 思路 | ✅ 对齐 |
| Restrained bold | §3.1 引用了「每 400 字 1-2 个粗体短语」，但未修订现有 heading weight-600 | ⚠️ 部分对齐 (见 A-4) |
| Display tracking `-0.02em ~ -0.05em` | 定义了 tracking tokens 但未建立 level→tracking 映射 | ⚠️ 部分对齐 (见 A-3) |
| Pull quote: regular/light weight, no container | 定义了 pullquote class，未提及容器禁令 | ⚠️ 需在实施规范中补充 |
| Body measure 60-70 ch | 未定义 `--measure-body` 或 max-width 约束 | ⚠️ 建议增加 |
| Body line-height 1.6-1.7 | `--leading-relaxed: 1.65` 落在范围内 | ✅ 对齐 |
| Asymmetric rhythm | 未提及节奏交替原则 | ⚠️ 建议在 spacing 策略中加入 |
| No more than 2 pull quotes per article | 未提及数量限制 | ⚠️ 建议在实施规范中补充 |

### anti-ai-slop.md

| 罪 | ScholarAI 状态 | 对齐 |
|---|---|---|
| 1. Default Tailwind indigo | 已用 #d35400 | ✅ 未犯 |
| 2. Two-stop trust gradient | 内页无 hero，不适用 | ✅ 不适用 |
| 3. Emoji as feature icons | §3.3 已检查，但 section break 用 ✦ (见 A-6) | ⚠️ 部分 |
| 4. Sans on serif-bound display | Playfair Display 已绑 | ✅ 未犯 |
| 5. Rounded card + colored left-border | 改为 shadow-paper 硬阴影 | ✅ 修复方案合理 |
| 6. Invented metrics | 无 | ✅ 未犯 |
| 7. Filler copy | 无 | ✅ 未犯 |
| >12 raw hex outside :root | oklch 化后 hex 应降为 0 | ✅ 方向正确 |
| `var(--accent)` 6+ times | 限制 2 per screen | ✅ 对齐 |

### color.md

| Craft 要求 | Research 对齐 | 状态 |
|---|---|---|
| Avoid pure black and pure white | light `--color-surface` 为 pure white | ❌ 违反 (见 A-1) |
| Dark: semi-transparent white borders | 暗色 border 用 `oklch(1 0 0 / 0.08)` | ✅ 完全对齐 |
| Accent discipline: ≤2 visible per screen | 已纳入规范 | ✅ 对齐 |
| Body text contrast ≥ 4.5:1 | accent 在白底上 ≈ 2.89:1，未定义 darken 变体 | ❌ 不满足 (见 A-2) |
| Dark theme: not inverse, independent palette | 独立色板策略明确 | ✅ 对齐 |
| Semantic color naming (purpose, not hue) | `--color-evidence-supported` 等按功能命名 | ✅ 对齐 |

---

**总结**: 研究文档的设计判断力和方向感整体优秀，核心问题集中在色彩精确度（纯白 surface、accent 对比度、暗色 chroma）和 editorial craft 的细粒度映射（tracking/weight/body-measure 显式绑定）上。这些都属于可快速修正的规范补充，不涉及架构方向变更。
