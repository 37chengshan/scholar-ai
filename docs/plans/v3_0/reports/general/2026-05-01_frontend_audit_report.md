# ScholarAI 前端代码审查报告

**审查范围:** `apps/web/src/` (447个源文件)、`packages/`
**审查日期:** 2026-05-01

---

## 一、安全问题 (CRITICAL/HIGH)

### CRITICAL-01: dangerouslySetInnerHTML 存在 XSS 风险

**文件:**
- `apps/web/src/app/components/NoteList.tsx` 第388行
- `apps/web/src/app/components/TypingText.tsx` 第153行
- `apps/web/src/app/components/MarkdownEditor.tsx` 第103行

`NoteList.tsx` 直接将 `note.content` 注入 HTML，未经过任何净化处理。如果 note 内容包含用户输入或来自后端未转义的数据，攻击者可注入恶意脚本。`TypingText.tsx` 的 `parsedHtml` 和 `MarkdownEditor.tsx` 的 `simpleMarkdownToHtml(value)` 同样存在此问题。

**建议:** 使用 DOMPurify 或类似的 HTML 净化库对所有 `dangerouslySetInnerHTML` 的值进行消毒。

---

### CRITICAL-02: console.log 泄露 API 请求/响应数据

**文件:**
- `apps/web/src/utils/apiClient.ts` 第154、204、246、292行
- `apps/web/src/app/hooks/useSessions.ts` 第101、158行

`apiClient.ts` 的请求/响应拦截器在 `import.meta.env.DEV` 条件下输出完整请求体和响应数据，包括用户凭证和会话信息。`useSessions.ts` 也有多处 `console.log`。虽然有 DEV 守卫，但在开发环境调试时仍可能泄露敏感数据到浏览器控制台，且如果 DEV 判断失效则直接暴露到生产环境。

**建议:** 使用结构化日志库替代 `console.log`，确保生产环境完全禁用。删除 `useSessions.ts` 中的调试日志。

---

### CRITICAL-03: APIKeyManager 使用原生 prompt() 输入密码

**文件:** `apps/web/src/app/components/APIKeyManager.tsx` 第67行

```typescript
const password = prompt('Enter your password to delete this API key:');
```

原生 `prompt()` 无法进行输入验证、无法设置 `type="password"`（虽然浏览器默认隐藏输入），且用户体验差。更严重的是，密码以明文形式在 JavaScript 中传递。

**建议:** 替换为自定义的密码确认对话框组件，使用受控的 `<input type="password">` 表单。

---

### HIGH-01: Mock 认证模块使用 localStorage 存储 token

**文件:** `apps/web/src/mocks/auth.ts` 第40-41、68-69行

Mock 模块将认证 token 和用户数据存入 localStorage。虽然正式认证使用 Cookie（HttpOnly），但 mock 代码可能被意外引入生产路径，且 localStorage 中的 token 容易被 XSS 攻击窃取。

**建议:** 确保 mock 模块在生产构建中被 tree-shake 或显式排除。在 vite.config.ts 中配置条件导入。

---

### HIGH-02: 生产环境 API 基础 URL 硬编码

**文件:** `apps/web/src/config/api.ts` 第34行

```typescript
return 'https://api.scholarai.com';
```

生产环境 fallback URL 硬编码在源码中。如果域名变更或存在多个部署环境，需要重新构建。

**建议:** 移除硬编码 URL，要求通过 `VITE_API_BASE_URL` 环境变量显式配置，构建时验证。

---

### HIGH-03: CSRF 保护不明确

**文件:** `apps/web/src/utils/apiClient.ts`

虽然使用了 `withCredentials: true` 的 Cookie 认证，但未看到 CSRF token 的发送机制。对于状态变更的 POST/PUT/DELETE 请求，仅依赖 Cookie 可能存在 CSRF 风险。

**建议:** 确认后端是否通过 SameSite cookie 属性或其他机制防护 CSRF。如无，需在请求头中添加 CSRF token。

---

## 二、性能问题 (HIGH/MEDIUM)

### HIGH-04: 重型依赖未做代码分割

**文件:** `apps/web/package.json`

以下重型库作为直接依赖被打包，未做动态导入或代码分割：
- `mermaid` (~1MB+) - 仅 MarkdownRenderer 使用
- `pdfjs-dist` (~2MB+) - 仅 PDF 阅读器使用
- `katex` (~300KB+) - 仅数学公式渲染使用
- `highlight.js` (~500KB+) - 仅代码块使用
- `@mui/material` + `@emotion/*` (~500KB+) - 不确定实际使用范围
- `recharts` (~400KB+) - 仅 Analytics 页面使用

这些库加起来可能使初始 bundle 增加 4-5MB。

**建议:** 对 `mermaid`、`pdfjs-dist`、`recharts` 使用动态 `import()` 延迟加载。评估 MUI 是否被实际使用，如未使用则移除。

---

### HIGH-05: 全局 CSS 选择器对所有元素应用 transition

**文件:** `apps/web/src/styles/global.css` 第49-51行

```css
* {
  transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
}
```

对所有元素设置 `transition-timing-function` 会导致浏览器为每个 DOM 元素维护过渡属性，影响渲染性能，尤其在大型列表或频繁更新的组件（如 Chat 消息流）中。

**建议:** 仅在需要过渡效果的元素/类上显式设置，或使用 Tailwind 的 `transition-*` 工具类。

---

### MEDIUM-01: ChatWorkspaceV2 组件过大，useEffect 过多

**文件:** `apps/web/src/features/chat/workspace/ChatWorkspaceV2.tsx` (757行)

该组件包含：
- 20+ 个 useState
- 10+ 个 useEffect
- 8+ 个 useMemo/useCallback
- 多个自定义 hook 的组合

虽然已通过自定义 hook 拆分了部分逻辑，但组件本身仍然是一个"上帝组件"，难以维护和测试。

**建议:** 进一步拆分：将 session 管理、streaming 逻辑、UI 渲染分离为独立的子组件或组合式 hook。

---

### MEDIUM-02: Layout 组件在每次渲染时创建新 URLSearchParams

**文件:** `apps/web/src/app/components/Layout.tsx` 第140行

```typescript
const currentQuery = new URLSearchParams(location.search);
```

在组件函数体内（非 useMemo）每次渲染都创建新的 URLSearchParams 对象。

**建议:** 使用 `useMemo` 包裹。

---

## 三、状态管理问题 (HIGH/MEDIUM)

### HIGH-06: useAuth 中的 checkAuth 函数引用不稳定

**文件:** `apps/web/src/contexts/AuthContext.tsx` 第106-136行

`checkAuth` 函数在每次渲染时重新创建（没有 `useCallback`），但被用在 `useEffect` 的依赖中（第200行的空依赖数组）。虽然空依赖数组避免了重复调用，但 `login` 和 `logout` 函数同样没有 `useCallback`，作为 context value 传递时会导致所有消费组件不必要的重渲染。

**建议:** 使用 `useCallback` 稳定 `login`、`logout`、`checkAuth` 函数引用。

---

### MEDIUM-03: SSE Service 单例与组件实例冲突

**文件:**
- `apps/web/src/services/sseService.ts` 第673行 - 导出单例 `sseService`
- `apps/web/src/features/chat/workspace/ChatWorkspaceV2.tsx` 第249行 - 创建新实例

`chatApi.ts` 使用全局单例 `sseService`，但 `ChatWorkspaceV2` 在 useEffect 中创建了自己的 `SSEService` 实例。`streamMessage` 函数通过 `streamService` 参数接受自定义实例，但 `stopStream()` 仍然断开全局单例。如果用户在 Chat 页面，停止操作可能无法正确停止实际的流。

**建议:** 统一 SSE 实例管理，要么全部使用组件实例，要么全部使用单例。

---

### MEDIUM-04: AuthContext 和 AuthStore 重复管理认证状态

**文件:**
- `apps/web/src/contexts/AuthContext.tsx`
- `apps/web/src/stores/authStore.ts`

AuthContext 内部使用 AuthStore，但同时暴露了 `user`、`isAuthenticated`、`loading` 等状态。这种双重包装增加了复杂性，且组件可以直接访问 store 绕过 context。

**建议:** 二选一：要么纯 context（移除 store），要么纯 store（移除 context，使用 Zustand 的 `useStore` hook）。

---

## 四、错误处理问题 (HIGH/MEDIUM)

### HIGH-07: ErrorBoundary 未覆盖路由级别

**文件:**
- `apps/web/src/app/App.tsx` 第12行 - 顶层 ErrorBoundary
- `apps/web/src/app/components/ErrorBoundary.tsx`

ErrorBoundary 仅在 App 最外层包裹一次。如果某个页面组件崩溃，整个应用会显示错误页面，用户必须刷新才能恢复。

**建议:** 在路由级别（每个页面组件外）添加 ErrorBoundary，实现局部错误隔离。错误恢复按钮应提供"返回首页"选项。

---

### HIGH-08: SSE 流错误处理不完整

**文件:** `apps/web/src/services/sseService.ts` 第583行

```typescript
} catch (err) {
  console.error('[SSE] Failed to parse event:', err, dataStr);
}
```

JSON 解析失败时仅 console.error，不通知上层。如果后端发送了格式错误的事件，前端会静默丢失该事件，用户看到的是流突然停止而无任何反馈。

**建议:** 解析失败时调用 `this.currentHandlers.onError()` 通知上层，并在 UI 中展示友好的错误提示。

---

### MEDIUM-05: API 客户端的 refresh 逻辑无并发请求排队

**文件:** `apps/web/src/utils/apiClient.ts` 第261-306行

当多个请求同时收到 401 时，每个请求都会独立触发 token refresh。虽然 `_retry` 标记防止了单个请求的无限重试，但多个并发请求会同时发起多个 refresh 请求，造成不必要的后端压力。

**建议:** 实现 refresh 锁机制：第一个 401 触发 refresh，后续 401 等待同一个 refresh Promise 完成后再重试。

---

## 五、可访问性问题 (MEDIUM/LOW)

### MEDIUM-06: 表单输入缺少 htmlFor/id 关联

**文件:**
- `apps/web/src/app/pages/Login.tsx` 第278-285行
- `apps/web/src/app/pages/Register.tsx` 第196-208行

所有 `<label>` 元素没有 `htmlFor` 属性，对应的 `<input>` 也没有 `id` 属性。屏幕阅读器无法正确关联标签和输入框。

**建议:** 为每个 input 添加唯一 id，label 添加对应的 htmlFor。

---

### MEDIUM-07: Chat 流式输出缺少 aria-live 区域

**文件:** `apps/web/src/features/chat/workspace/ChatWorkspaceV2.tsx`

Chat 消息流式输出时，新内容逐步追加但没有 `aria-live` 区域通知屏幕阅读器。唯一的 `aria-live="polite"` 在第677行用于 scopeHint，不是用于消息内容。

**建议:** 为消息列表容器添加 `aria-live="polite"` 和 `aria-atomic="false"`。

---

### MEDIUM-08: 颜色对比度可能不足

**文件:** `apps/web/src/styles/theme.css`

- `--color-muted-foreground: #7a6b5d` 在 `--color-background: #fdfaf6` 上的对比度约为 4.2:1，刚好达到 AA 标准但未达 AAA
- 多处使用 `text-foreground/60`、`text-foreground/55` 等透明度，实际对比度可能低于 4.5:1

**建议:** 使用 WebAIM Contrast Checker 验证所有文本/背景组合的对比度。

---

## 六、代码质量问题 (HIGH/MEDIUM)

### HIGH-09: 大量使用 `any` 类型

**总计:** 41 个文件中有 92 处 `: any`

关键位置：
- `apps/web/src/services/sseService.ts` - 5处
- `apps/web/src/features/chat/workspace/ChatWorkspaceV2.test.tsx` - 6处
- `apps/web/src/app/pages/KnowledgeBaseList.tsx` - 5处

**建议:** 分批修复，优先处理服务层和 hooks 中的 `any`，使用 `unknown` + 类型守卫替代。

---

### HIGH-10: 重复组件 - SearchResultCard 和 ToolCallCard

**文件:**
- `apps/web/src/app/components/SearchResultCard.tsx`
- `apps/web/src/app/components/tools/SearchResultCard.tsx`
- `apps/web/src/app/components/ToolCallCard.tsx`
- `apps/web/src/app/components/tools/` 下的多个卡片组件

存在两套平行的组件目录结构：`app/components/` 和 `app/components/tools/`，部分组件功能重叠。

**建议:** 统一组件目录，删除重复组件，建立单一来源。

---

### MEDIUM-09: MUI 依赖可能未使用

**文件:** `apps/web/package.json` 第21-23行

```json
"@emotion/react": "11.14.0",
"@emotion/styled": "11.14.1",
"@mui/icons-material": "7.3.5",
"@mui/material": "7.3.5",
```

项目主要使用 Radix UI + Tailwind + lucide-react，MUI 和 Emotion 的引入增加了约 500KB+ 的 bundle 体积。需要确认 MUI 是否被实际使用。

**建议:** 搜索 MUI 组件的 import，如未使用则移除这四个依赖。

---

### MEDIUM-10: Mock 文件残留

**文件:** `apps/web/src/mocks/auth.ts`

Mock 认证模块仍然存在于源码中，包含 localStorage token 存储逻辑。虽然可能仅用于测试，但存在被意外引入生产路径的风险。

**建议:** 将 mock 文件移至 `__mocks__/` 目录或 `.test.` 文件中，确保不会进入生产 bundle。

---

## 七、样式问题 (MEDIUM/LOW)

### MEDIUM-11: 无暗色模式支持

**文件:** `apps/web/src/styles/theme.css`

主题仅定义了亮色模式的颜色变量。虽然依赖列表中有 `next-themes`，但未看到暗色模式的实际实现。`theme.css` 中没有 `[data-theme="dark"]` 或 `.dark` 选择器。

**建议:** 如需暗色模式，添加对应的暗色主题变量；如不需要，移除 `next-themes` 依赖。

---

### MEDIUM-12: 字体大小设置与 CSS 变量冲突

**文件:**
- `apps/web/src/stores/settingsStore.ts` - 设置 `--base-font-size`
- `apps/web/src/styles/theme.css` - 定义 `--font-xs` 到 `--font-xl`
- `apps/web/src/styles/global.css` - 使用 `--base-font-size`

`settingsStore` 修改 `--base-font-size`，但 `theme.css` 中的 `--font-xs/sm/md/lg/xl` 使用 `clamp()` 且不依赖 `--base-font-size`。这意味着用户的字体大小设置对使用 `var(--font-*)` 的组件无效。

**建议:** 统一字体大小系统，让 `--font-*` 变量引用 `--base-font-size` 或直接使用 rem 单位。

---

## 八、测试覆盖 (MEDIUM)

### MEDIUM-13: 关键页面缺少测试

**已有测试 (81个文件):** Chat、Search、KnowledgeBaseDetail、Settings、Analytics 等核心功能有测试覆盖。

**缺少测试的关键路径:**
- `apps/web/src/app/pages/Login.tsx` - 无测试
- `apps/web/src/app/pages/Register.tsx` - 无测试
- `apps/web/src/app/pages/Dashboard.tsx` - 无测试
- `apps/web/src/app/pages/ForgotPassword.tsx` - 无测试
- `apps/web/src/app/pages/ResetPassword.tsx` - 无测试
- `apps/web/src/app/components/APIKeyManager.tsx` - 无测试
- `apps/web/src/app/components/Layout.tsx` - 无测试
- `apps/web/src/stores/` - 所有 store 无测试

认证流程（登录/注册/密码重置）是安全关键路径，缺少测试是高风险。

**建议:** 优先为认证页面和 Zustand stores 添加单元测试。

---

## 问题汇总

| 严重程度 | 数量 | 关键领域 |
|---------|------|---------|
| CRITICAL | 3 | XSS、敏感数据泄露、密码输入 |
| HIGH | 10 | CSRF、bundle 体积、错误处理、类型安全、状态管理 |
| MEDIUM | 13 | a11y、暗色模式、测试覆盖、代码组织 |
| LOW | 0 | - |

**最优先修复:** CRITICAL-01 (XSS)、CRITICAL-02 (console.log 泄露)、HIGH-04 (bundle 体积)、HIGH-07 (ErrorBoundary)
