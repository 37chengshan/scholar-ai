# ScholarAI 设计系统集成规则

基于对 ScholarAI 前端代码库的深入分析，以下是为 Figma MCP 集成提供的设计系统规则文档。

---

## 1. 设计令牌定义 (Design Tokens)

### 1.1 颜色系统

**文件位置**: `scholar-ai/apps/web/src/styles/theme.css`

颜色令牌使用 CSS 变量定义，采用 Tailwind CSS v4 的 `@theme` 语法：

```css
@theme {
  /* Primary orange theme - ScholarAI brand color */
  --color-primary: #d35400;
  --color-primary-foreground: #ffffff;
  --color-secondary: #e67e22;
  --color-secondary-foreground: #ffffff;

  /* Background colors - warm paper-like aesthetic */
  --color-background: #fdfaf6;
  --color-card: #ffffff;
  --color-popover: #ffffff;

  /* Muted colors - subtle earth tones */
  --color-muted: #f4ece1;
  --color-muted-foreground: #7a6b5d;
  --color-foreground: #2d241e;
  --color-accent-foreground: #d35400;

  /* Status colors */
  --color-destructive: #d4183d;
  --color-border: rgba(45, 36, 30, 0.1);
  --color-ring: oklch(0.708 0 0);

  /* Chart colors (OKLCH color space) */
  --color-chart-1: oklch(0.646 0.222 41.116);
  --color-chart-2: oklch(0.6 0.118 184.704);
  --color-chart-3: oklch(0.398 0.07 227.392);
  --color-chart-4: oklch(0.828 0.189 84.429);
  --color-chart-5: oklch(0.769 0.188 70.08);

  /* Magazine landing page */
  --color-magazine-bg: #f4ece1;
}
```

### 1.2 排版系统 (Typography)

**字体族定义** (`scholar-ai/apps/web/src/styles/fonts.css`):

```css
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400..900;1,400..900&family=Outfit:wght@100..900&family=Noto+Serif+SC:wght@200..900&family=JetBrains+Mono:wght@100..800&display=swap');
```

**字体令牌** (`theme.css`):
```css
--font-serif: 'Playfair Display', 'Noto Serif SC', serif;
--font-sans: 'Outfit', sans-serif;
--font-mono: 'JetBrains Mono', monospace;
```

**字体用途**:
- **Playfair Display / Noto Serif SC**: 标题、杂志风格页面、学术论文标题
- **Outfit**: 正文、UI 元素、按钮、导航
- **JetBrains Mono**: 代码块、技术内容

### 1.3 间距与圆角 (Spacing & Radius)

```css
/* Border radius */
--radius: 0.625rem;    /* 10px - default */
--radius-sm: 0.375rem; /* 6px */
--radius-md: 0.5rem;   /* 8px */
--radius-lg: 0.625rem; /* 10px */
--radius-xl: 1rem;     /* 16px */
```

---

## 2. 组件库架构 (Component Library)

### 2.1 组件基础

**位置**: `scholar-ai/apps/web/src/app/components/ui/`

组件基于 **shadcn/ui** 模式构建，底层使用 **Radix UI** 原语：

| 组件 | 文件 | 底层依赖 |
|------|------|---------|
| Button | `button.tsx` | @radix-ui/react-slot |
| Card | `card.tsx` | 纯 CSS |
| Dialog | `dialog.tsx` | @radix-ui/react-dialog |
| Dropdown | `dropdown-menu.tsx` | @radix-ui/react-dropdown-menu |
| Select | `select.tsx` | @radix-ui/react-select |
| Tabs | `tabs.tsx` | @radix-ui/react-tabs |
| Tooltip | `tooltip.tsx` | @radix-ui/react-tooltip |

### 2.2 样式工具函数

**文件**: `scholar-ai/apps/web/src/app/components/ui/utils.ts`

```typescript
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

**使用方式**: 所有组件使用 `cn()` 函数合并 Tailwind 类名。

### 2.3 Button 组件示例

```tsx
import { cva, type VariantProps } from "class-variance-authority";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-all disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        destructive: "bg-destructive text-white hover:bg-destructive/90",
        outline: "border bg-background text-foreground hover:bg-accent",
        secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-9 px-4 py-2",
        sm: "h-8 rounded-md px-3",
        lg: "h-10 rounded-md px-6",
        icon: "size-9 rounded-md",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);
```

### 2.4 Card 组件示例

```tsx
function Card({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card"
      className={cn(
        "bg-card text-card-foreground flex flex-col gap-6 rounded-xl border",
        className,
      )}
      {...props}
    />
  );
}
```

### 2.5 自定义业务组件

**位置**: `scholar-ai/apps/web/src/app/components/`

| 组件 | 用途 |
|------|------|
| `PaperCard.tsx` | 论文卡片展示 |
| `MessageBubble.tsx` | 聊天消息气泡 |
| `PDFViewer.tsx` | PDF 预览器 |
| `MarkdownEditor.tsx` | Markdown 编辑器 |
| `SearchResultCard.tsx` | 搜索结果卡片 |
| `CitationsPanel.tsx` | 引用面板 |
| `NotesEditor.tsx` | 笔记编辑器 |
| `CodeBlock.tsx` | 代码块渲染 |
| `ThumbnailStrip.tsx` | 缩略图条 |

---

## 3. 框架与技术栈 (Frameworks & Libraries)

### 3.1 核心框架

| 技术 | 版本 | 用途 |
|------|------|------|
| React | 18.3.1 | UI 框架 |
| TypeScript | 5.4+ | 类型系统 |
| Tailwind CSS | 4.1.12 | 样式系统 |
| Vite | 6.3.5 | 构建工具 |

### 3.2 UI 库

| 库 | 版本 | 用途 |
|---|---|---|
| Radix UI | 各组件独立版本 | 无障碍原语组件 |
| Lucide React | 0.487.0 | 图标库 |
| class-variance-authority | 0.7.1 | 变体样式管理 |
| tailwind-merge | 3.2.0 | 类名合并 |
| motion | 12.23.24 | 动画库 |

### 3.3 状态管理

| 库 | 用途 |
|---|---|
| Zustand | 全局状态 (`src/stores/`) |
| TanStack Query | 服务端状态 (`src/lib/queryClient.ts`) |
| React Hook Form | 表单状态 |

### 3.4 路径别名

**配置**: `tsconfig.json` + `vite.config.ts`

```typescript
// tsconfig.json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}

// 使用示例
import { Button } from "@/app/components/ui/button";
import { useAuth } from "@/contexts/AuthContext";
```

---

## 4. 资产管理 (Asset Management)

### 4.1 字体资源

使用 Google Fonts CDN 加载：

```html
<!-- 在 fonts.css 中通过 @import 引入 -->
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400..900;1,400..900&family=Outfit:wght@100..900&family=Noto+Serif+SC:wght@200..900&family=JetBrains+Mono:wght@100..800&display=swap');
```

### 4.2 图片资产

**当前状态**: 项目未设置专门的 `assets/` 目录。

**推荐做法**:
- 将静态图片放在 `src/assets/images/`
- SVG 图标可放在 `src/assets/icons/` 或直接使用 Lucide React
- 使用 Vite 的 raw import 支持 SVG、CSV、HTML

```typescript
// vite.config.ts 已配置
assetsInclude: ['**/*.svg', '**/*.csv', '**/*.html']
```

---

## 5. 图标系统 (Icon System)

### 5.1 图标库

**使用**: Lucide React (`lucide-react`)

**导入方式**:
```tsx
import {
  Search,
  ArrowRight,
  FileText,
  UploadCloud,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Check,
  Copy
} from 'lucide-react';
```

### 5.2 图标命名约定

- 使用 PascalCase 命名
- 遵循 Lucide 的图标命名规范
- 常用图标别名示例：
  - `ExternalLink as ExternalLinkIcon` (避免与组件名冲突)

### 5.3 图标使用规范

```tsx
// 在按钮中使用
<Button variant="ghost" size="icon">
  <Search className="h-4 w-4" />
</Button>

// 带文字
<Button>
  <UploadCloud className="mr-2 h-4 w-4" />
  上传论文
</Button>
```

### 5.4 常用图标列表

| 图标名 | 用途 |
|--------|------|
| `Search` | 搜索 |
| `ArrowRight`, `ArrowLeft` | 导航箭头 |
| `FileText` | 文件/论文 |
| `UploadCloud` | 上传 |
| `Folder` | 文件夹 |
| `Star` | 收藏 |
| `Check`, `CheckCircle2` | 成功/完成 |
| `X`, `Trash2` | 删除/关闭 |
| `ChevronDown`, `ChevronUp` | 展开/收起 |
| `ExternalLink` | 外部链接 |
| `Copy`, `Check` | 复制操作 |
| `RefreshCw` | 刷新 |
| `Settings2` | 设置 |
| `User` | 用户 |
| `Activity` | 活动/统计 |

---

## 6. 样式方法 (Styling Approach)

### 6.1 Tailwind CSS v4 配置

**文件**: `scholar-ai/apps/web/src/styles/tailwind.css`

```css
@import 'tailwindcss' source(none);
@source '../**/*.{js,ts,jsx,tsx}';
@import 'tw-animate-css';
```

### 6.2 样式文件组织

```
src/styles/
├── index.css      # 主入口，导入所有样式
├── fonts.css      # 字体定义
├── tailwind.css   # Tailwind 配置
├── theme.css      # 设计令牌
├── global.css     # 全局样式
└── magazine.css   # 杂志风格页面样式
```

### 6.3 全局样式 (`global.css`)

```css
/* 滚动条样式 */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: rgba(45, 36, 30, 0.05);
}

::-webkit-scrollbar-thumb {
  background: rgba(45, 36, 30, 0.2);
  border-radius: 4px;
}

/* 动画 */
@keyframes spin { ... }
@keyframes fadeIn { ... }
@keyframes slideUp { ... }

/* 移动端优化 */
@media (hover: none) and (pointer: coarse) {
  button, a, input[type="checkbox"], input[type="radio"] {
    min-height: 44px;
    min-width: 44px;
  }
}
```

### 6.4 响应式设计

**断点**: 使用 Tailwind 默认断点

```tsx
// 移动优先
<div className="px-4 md:px-6 lg:px-8">
  <h1 className="text-2xl md:text-3xl lg:text-4xl">
    标题
  </h1>
</div>
```

### 6.5 暗色模式

**当前状态**: 项目主要支持浅色主题

**设计令牌未包含暗色变量**，如需扩展：

```css
@theme {
  --color-background: #fdfaf6;
  /* 需要添加 dark: 变体 */
}
```

---

## 7. 项目结构 (Project Structure)

### 7.1 目录组织

```
scholar-ai/apps/web/src/
├── app/                    # 应用核心
│   ├── components/         # 组件
│   │   ├── ui/            # 基础 UI 组件
│   │   ├── landing/       # 落地页组件
│   │   └── notes/         # 笔记相关组件
│   ├── pages/             # 页面组件
│   ├── contexts/          # React Context
│   └── hooks/             # 自定义 Hooks
├── components/             # 共享组件
├── contexts/               # 全局 Context (Auth)
├── hooks/                  # 全局 Hooks
├── lib/                    # 工具库
├── services/               # API 服务
├── stores/                 # Zustand 状态
├── styles/                 # 样式文件
├── types/                  # TypeScript 类型
└── utils/                  # 工具函数
```

### 7.2 命名约定

| 类型 | 约定 | 示例 |
|------|------|------|
| 组件文件 | PascalCase.tsx | `Button.tsx`, `PaperCard.tsx` |
| 页面文件 | PascalCase.tsx | `Landing.tsx`, `Dashboard.tsx` |
| Hook 文件 | camelCase.ts | `useUpload.ts`, `useSessions.ts` |
| 服务文件 | camelCase.ts | `authApi.ts`, `papersApi.ts` |
| 类型文件 | camelCase.ts | `index.ts`, `chat.ts` |
| 样式文件 | kebab-case.css | `global.css`, `tailwind.css` |

### 7.3 类型定义

**位置**: `scholar-ai/apps/web/src/types/`

```typescript
// 核心实体类型
interface User { id: string; email: string; name: string; ... }
interface Paper { id: string; title: string; authors: string[]; ... }
interface Session { id: string; title?: string; ... }
interface Message { id: string; role: 'user' | 'assistant'; content: string; ... }

// API 响应类型
interface LoginResponse { success: boolean; data?: { user: User }; ... }
interface PapersListResponse { success: boolean; data: { papers: Paper[]; total: number }; }
```

---

## 8. Figma 集成建议 (Figma Integration)

### 8.1 设计令牌映射

在 Figma 中创建以下变量集合：

| 变量集合 | 值来源 |
|---------|--------|
| colors-primary | `--color-primary` (#d35400) |
| colors-background | `--color-background` (#fdfaf6) |
| colors-muted | `--color-muted` (#f4ece1) |
| typography-font-sans | Outfit |
| typography-font-serif | Playfair Display |
| spacing-radius | `--radius` 系列 |

### 8.2 组件映射

| Figma 组件 | 代码实现 |
|-----------|---------|
| Button | `src/app/components/ui/button.tsx` |
| Card | `src/app/components/ui/card.tsx` |
| Input | `src/app/components/ui/input.tsx` |
| Dialog | `src/app/components/ui/dialog.tsx` |
| Select | `src/app/components/ui/select.tsx` |
| Tabs | `src/app/components/ui/tabs.tsx` |
| Tooltip | `src/app/components/ui/tooltip.tsx` |

### 8.3 Code Connect 配置示例

```typescript
// 推荐 Code Connect 映射示例
{
  "Button": {
    "source": "src/app/components/ui/button.tsx",
    "importPath": "@/app/components/ui/button",
    "variants": ["default", "destructive", "outline", "secondary", "ghost", "link"],
    "sizes": ["default", "sm", "lg", "icon"]
  },
  "Card": {
    "source": "src/app/components/ui/card.tsx",
    "importPath": "@/app/components/ui/card",
    "parts": ["Card", "CardHeader", "CardTitle", "CardDescription", "CardContent", "CardFooter"]
  }
}
```

### 8.4 设计原则

1. **颜色一致性**: 使用项目定义的 CSS 变量，避免硬编码颜色值
2. **响应式优先**: 设计需考虑移动端到桌面端的响应式布局
3. **无障碍**: 基于 Radix UI 的组件确保无障碍访问
4. **杂志风格**: 落地页采用温暖的学术风格，背景色 `#f4ece1`

---

## 9. 开发环境 (Development Environment)

### 9.1 启动命令

```bash
cd scholar-ai/frontend
npm run dev      # 启动开发服务器
npm run build    # 构建生产版本
npm run test     # 运行测试
npm run type-check  # TypeScript 类型检查
```

### 9.2 API 代理配置

```typescript
// vite.config.ts
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
}
```

### 9.3 依赖安装

```bash
npm install
```

---

## 10. 设计系统总结

ScholarAI 前端采用现代化的技术栈：

| 层面 | 技术 |
|------|------|
| **样式系统** | Tailwind CSS v4 + CSS 变量设计令牌 |
| **组件模式** | shadcn/ui 模式 + Radix UI 原语 |
| **图标** | Lucide React |
| **字体** | Google Fonts (Playfair Display, Outfit, Noto Serif SC, JetBrains Mono) |
| **品牌色** | 橙色系 (#d35400 主色) |
| **设计风格** | 温暖、学术、杂志风格 |

**核心价值**: 设计系统服务于学术论文阅读场景，强调温暖、专业的阅读体验。

---

*文档生成时间: 2026-04-09*