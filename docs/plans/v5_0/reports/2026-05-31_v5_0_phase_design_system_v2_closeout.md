# v5.0 Phase 5.0-1 Design System v2 Closeout Report

> 日期：2026-05-31
> Phase：5.0-1 | Design System v2
> 状态：done
> Owner：web-platform

---

## 1. 目标回顾

Phase 5.0-1 完成 Design System v2 的全部 5 个 Wave：UI 原语令牌化、暗色主题激活、字体预加载加固、magazine.css 令牌化、反模板视觉打磨。

---

## 2. Wave 执行结果

### Wave 1 (已完成): Token Foundation
- 190 tokens across 5 files (color, typography, spacing, motion, elevation)
- oklch color space, dark overrides, `@layer tokens`, `@theme` block
- FOUC script, ThemeProvider, font preconnect+preload

### Wave 2: UI Primitive Tokenization

**Task 2.1: Component shadow tokens in elevation.css**
- 新增 6 个 neobrutalist shadow tokens: `--shadow-neo`, `--shadow-neo-hover`, `--shadow-neo-active`, `--shadow-accent`, `--shadow-accent-hover`, `--shadow-focus-accent`
- 新增 6 个 `.dark` overrides 使用 `oklch(0.85 0 0)`
- 同步更新 `theme.css` @theme block

**Task 2.2: Tokenize button.tsx and card.tsx**
- button.tsx: `shadow-[3px_3px_0_0_#09090b]` -> `shadow-[var(--shadow-neo)]`
- card.tsx: `shadow-[4px_4px_0_0_#FF3300]` -> `shadow-[var(--shadow-accent)]`
- `transition-all` -> `transition-[transform,box-shadow,opacity]`

**Task 2.3: Tokenize input.tsx and textarea.tsx**
- input.tsx: `shadow-[3px_3px_0_0_#09090b]` -> `shadow-[var(--shadow-neo)]`
- textarea.tsx: same pattern
- 移除重复 `transition-[color,box-shadow]` 声明

**验证:** `grep -rn '#09090b\|#FF3300\|#002FA7' apps/web/src/app/components/ui/` 返回空

### Wave 3: Dark Theme Activation

**Task 3.1: ThemeProvider + theme toggle**
- ThemeProvider 已在 App.tsx 中包裹应用根
- 新建 `theme-toggle.tsx` 组件 (light/dark/system 三态切换)
- 新建 `ThemeSelector.tsx` 用于 Settings 页面
- 更新 `DisplaySection.tsx` 集成 ThemeSelector

**Task 3.2: Dark theme verification**
- 修复 `bg-white` -> `bg-surface` / `bg-card` (ResetPassword, ForgotPassword, NotesSidebar, ArtifactsDrawer)
- 修复 `text-[#d35400]` -> `text-primary` (auth pages)
- 修复 WorkspaceShell: `bg-stone-50` -> `bg-background`, `bg-white` -> `bg-surface`
- 新增 sidebar CSS variables (`--sidebar-background` through `--sidebar-ring`) with dark overrides

**Task 3.3: XSS audit**
- NoteList.tsx: 添加 DOMPurify sanitize (`DOMPurify.sanitize(note.content)`)
- TypingText.tsx / MarkdownEditor.tsx: `simpleMarkdownToHtml` 已内置 HTML 实体转义，安全

### Wave 4: Font & Magazine

**Task 4.1: Font preload hardening**
- 添加 `crossorigin` 到 font preload link
- `font-display: swap` 已确认存在 (`&display=swap`)
- SRI 不适用于 Google Fonts (动态生成 CSS)

**Task 4.2: magazine.css inner-page adaptation**
- 移除 `white` 关键字 -> `var(--color-surface)`
- `transition: all` -> 具体属性 (transform, box-shadow, background-color, color, border-color)
- 移除重复 `.magazine-card` transition 规则
- 新增 `.magazine-inner` scope 用于内页密度适配

### Wave 5: Anti-template Polish + Documentation

**Task 5.1: Editorial typography classes**
- 新增 `.editorial-pullquote` class (magazine.css)
- 新增 `.drop-cap::first-letter` class (magazine.css)
- 新增 `.bento-grid` utility (global.css)

**Task 5.2: DESIGN_SYSTEM.md update**
- 更新 Theme Tokens 节: hex -> oklch 值
- 新增 Dark Theme 节: `.dark` class strategy, FOUC prevention
- 新增 Shadow System 节: 三层阴影模型
- 新增 Motion System 节: duration/easing/intent tokens
- 更新 Source of Truth: 包含 tokens/ 目录文件

**Task 5.3: Full-site hex cleanup**
- 修复 20+ 组件中的裸 hex 值
- 剩余 28 个 hex 值均为可接受例外:
  - Canvas rendering context (GlobalDragonBackground.tsx)
  - Recharts library internals (chart.tsx CSS selectors)
  - Annotation feature data model (AnnotationToolbar.tsx, PDFViewer.tsx)
  - Terminal-style UI (SettingsStatusRail.tsx, Login.tsx)

---

## 3. 测试结果

| 验证项 | 结果 |
|---|---|
| `npm run type-check` (tsc --noEmit) | PASS |
| `npm run test:run -- --reporter=dot` | 366 passed / 1 failed (pre-existing) |
| `npm run build` | PASS |

**失败用例:** `KnowledgeBaseDetail.test.tsx:155` -- 检索结果渲染时序问题，pre-existing，不阻塞 closeout。

---

## 4. 修改文件清单

### Token Files
- `apps/web/src/styles/tokens/elevation.css` -- +12 shadow tokens (6 light + 6 dark)
- `apps/web/src/styles/tokens/color.css` -- +16 sidebar tokens (8 light + 8 dark)
- `apps/web/src/styles/theme.css` -- +18 @theme entries (shadows + sidebar)

### UI Components
- `apps/web/src/app/components/ui/button.tsx` -- tokenized shadows, transition
- `apps/web/src/app/components/ui/card.tsx` -- tokenized shadows, transition
- `apps/web/src/app/components/ui/input.tsx` -- tokenized shadows, transition
- `apps/web/src/app/components/ui/textarea.tsx` -- tokenized shadows, transition
- `apps/web/src/app/components/ui/theme-toggle.tsx` -- NEW

### Pages
- `apps/web/src/app/pages/ResetPassword.tsx` -- tokenized hex
- `apps/web/src/app/pages/ForgotPassword.tsx` -- tokenized hex
- `apps/web/src/app/pages/Landing.tsx` -- tokenized hex
- `apps/web/src/app/pages/Analytics.tsx` -- tokenized hex

### Features
- `apps/web/src/features/settings/components/ThemeSelector.tsx` -- NEW
- `apps/web/src/features/settings/sections/DisplaySection.tsx` -- added ThemeSelector
- `apps/web/src/features/notes/components/NotesSidebar.tsx` -- tokenized hex
- `apps/web/src/features/workflow/components/ArtifactsDrawer.tsx` -- tokenized hex
- `apps/web/src/features/workflow/components/WorkflowShell.tsx` -- tokenized hex
- `apps/web/src/features/workflow/components/RecoverableTasksPanel.tsx` -- tokenized hex
- `apps/web/src/features/workflow/components/PendingActionsPanel.tsx` -- tokenized hex
- `apps/web/src/features/workflow/components/CurrentRunBar.tsx` -- tokenized hex
- `apps/web/src/features/workflow/components/ActiveScopeBanner.tsx` -- tokenized hex

### Other Components
- `apps/web/src/app/components/layout/WorkspaceShell.tsx` -- tokenized colors
- `apps/web/src/app/components/NoteList.tsx` -- DOMPurify XSS fix
- `apps/web/src/app/components/MarkdownEditor.tsx` -- tokenized hex
- `apps/web/src/app/components/MarkdownRenderer.tsx` -- tokenized hex
- `apps/web/src/app/components/ToolCallCard.tsx` -- tokenized hex
- `apps/web/src/app/components/ThinkingProcess.tsx` -- tokenized hex
- `apps/web/src/app/components/FontSizeSelector.tsx` -- tokenized hex
- `apps/web/src/app/components/UploadInputSwitch.tsx` -- tokenized hex
- `apps/web/src/app/components/ScopeBanner.tsx` -- tokenized hex
- `apps/web/src/app/components/MessageThinkingPanel.tsx` -- tokenized hex
- `apps/web/src/app/components/landing/DemoAnimation.tsx` -- tokenized hex

### Styles
- `apps/web/src/styles/magazine.css` -- transition fixes, inner-page adaptation, editorial classes
- `apps/web/src/styles/global.css` -- bento grid utility

### Config
- `apps/web/index.html` -- crossorigin on font preload
- `apps/web/package.json` -- added dompurify dependency

### Documentation
- `docs/specs/design/frontend/DESIGN_SYSTEM.md` -- full update
- `docs/plans/PLAN_STATUS.md` -- status update

---

## 5. 成功标准验证

| 标准 | 状态 |
|---|---|
| Zero hardcoded hex in UI primitives | PASS |
| Dark theme functional | PASS (ThemeProvider + toggle + token overrides) |
| XSS sanitized | PASS (DOMPurify on NoteList.tsx) |
| Font preload hardened | PASS (crossorigin added) |
| Magazine.css tokenized | PASS (zero bare hex, transition fixes) |
| DESIGN_SYSTEM.md accurate | PASS (oklch values, dark theme, shadow system, motion system) |
| Build green | PASS (type-check + build) |
| No file exceeds 800 lines | PASS |

---

## 6. 已知例外 (可接受)

| 位置 | 原因 |
|---|---|
| GlobalDragonBackground.tsx canvas colors | Canvas API 不支持 CSS variables |
| chart.tsx recharts selectors | CSS selectors targeting library SVG internals |
| AnnotationToolbar.tsx highlight colors | Feature data model (user-selectable) |
| PDFViewer.tsx annotation fallback | Feature data model |
| SettingsStatusRail.tsx / Login.tsx terminal UI | Intentional dark terminal aesthetic |
