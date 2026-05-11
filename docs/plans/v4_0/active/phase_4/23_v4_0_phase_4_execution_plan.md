# v4.0-4 详细执行计划：Frontend Experience Craft

> 日期：2026-05-10
> 状态：completed（2026-05-11）
> 上游研究：`docs/plans/v4_0/active/phase_4/2026-05-08_v4_0_phase_4_frontend_experience_craft_research.md`
> 上游总览：`docs/plans/v4_0/active/overview/18_v4_0_overview_plan.md`

## 1. 目标与约束

**本阶段核心目标**：把 ScholarAI 已形成的主研究流程打磨到可展示、可解释、可连续使用的前端表达质量。

**本阶段核心约束**（源自研究文档）：
1. **不做**：引新设计系统、引新组件库、重做信息架构、重做响应式/无障碍/性能优化（留到 4.0-5）、擅自写死依赖 Phase 4.0-3 的 artifact 视图。
2. **必做**：统一 Workspace Shell、统一状态语义组件、剥离 God Page 庞大单体内容、按优先级完成页面 UI Polish。
3. Phase 4.0-3 contract 仍未收口，所有相关的 Review Artifact / Compare Matrix 只准备基础壳层容器。

## 2. 核心交互规范与 UI 体验细节 (Interaction & UX Specs)

在剥离庞大的 God Page 之前，必须先明确前端界面的微交互、状态切换、延时策略及多栏拖拽手感，确保呈现出“暖纸张学术感”和高密度数据展示的稳重感。

### 2.1 交互体验基线原则
1. **防闪烁与过渡 (State Transitions & Anti-Flicker)**:
   - 从数据请求到返回，必须有保底 **200ms** 的延迟才显示 Loading，防止快请求导致的画面剧烈闪烁 (采用 `useDeferredValue` 或 Tailwind delay class 结合 opacity)。
   - 面板切换和条件渲染，必须采用 `fade-in`，避免硬切割 (Hard cuts)。
2. **焦点与按键反馈 (Focus & Focus-Visible)**:
   - 彻底废弃仅靠 `hover` 的隐性交互。所有可交互元素必须具备明确的 `:active` 收缩感反馈（如 `active:scale-[0.98]`）。
   - 键盘导航空隙必须有完整的 `focus-visible:ring-2 focus-visible:ring-orange-500/50 focus-visible:outline-none focus-visible:ring-offset-2 focus-visible:ring-offset-stone-50` 约束。
3. **Typography & Layout 暖卷宗感 (全站字体优化)**:
   - 全面优化全站字体栈 (Font Stack)，提供更具学术和专业感的排版。正文、标题与代码使用精心调配的无衬线与衬线字体组合，优化字重与行高。
   - 杜绝纯白 (`bg-white`) 与纯黑 (`text-black`) 引起的视觉刺眼，广泛使用 `bg-stone-50` 起底，辅以 `text-stone-800` 和 `text-stone-600`。
   - 文本宽度极值控制在 `max-w-prose` (约 65-70ch)，确保最佳学术阅读行长。长摘要区块如若受限，引入 `@chenglou/pretext` 处理截断与障碍物绕排。
4. **多栏可拉伸面板 (Resizable Panels) 手感**:
   - Splitter（分割线）静默状态下宽度为 1px，`hover` 时在不改变占位大小的情况下视觉扩展为辅助色，提供足够的 hit area (拖拽感应区)。
   - 提供双击 Splitter 回归默认比例、或依靠 `collapsible` 直接吸附收拢。
   - 响应 `prefers-reduced-motion`，若系统开启减弱动画，自动禁用复杂的卡片滑动或折叠弹性展开。
5. **Sidebar (左侧栏) 视觉密度与空间控制**:
   - 严格控制左侧主导航/功能栏项目的占位大小与垂直空间。
   - 默认视图下仅直接平铺展示 2-3 个最高频核心功能项。
   - 更多功能放入带阴影与滚条提示的溢出容器 (`ScrollArea`) 中，通过向下滑动浏览。将宝贵的侧边栏垂直区域让渡给工作列表和当前上下文。

## 3. 标准 UI 原语与代码落地方案

### 3.1 增强交互态的基础按钮层 (Button CVA)
统一全站按钮，强制下发焦点、按下与悬停交互反馈：

```tsx
// apps/web/src/app/components/ui/button.tsx
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';
import * as React from 'react';

const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-md font-medium transition-all duration-200 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/50 focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none active:scale-[0.98]",
  {
    variants: {
      variant: {
        primary: "bg-orange-600 text-white hover:bg-orange-700 shadow-sm hover:shadow-md",
        secondary: "bg-stone-200/50 text-stone-800 hover:bg-stone-300/60 border border-stone-200/40",
        ghost: "bg-transparent text-stone-600 hover:bg-stone-100 hover:text-stone-900",
      },
      size: {
        sm: "h-8 px-3 text-sm",
        md: "h-10 px-4 py-2",
        icon: "h-9 w-9",
      },
    },
    defaultVariants: { variant: "primary", size: "md" }
  }
);
export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {}
export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(({ className, variant, size, ...props }, ref) => (
  <button ref={ref} className={cn(buttonVariants({ variant, size, className }))} {...props} />
));
Button.displayName = "Button";
```

### 3.2 具有动效和情感的状态表达组合 `UnifiedFeedbackState.tsx`
承接 Loading、Error、Empty、Partial 的统一渲染。

```tsx
// apps/web/src/app/components/UnifiedFeedbackState.tsx
import { cva, type VariantProps } from 'class-variance-authority';
import { AlertCircle, FileQuestion, Loader2, Info } from 'lucide-react';
import { cn } from '@/lib/utils';

const feedbackVariants = cva(
  "flex flex-col items-center justify-center p-8 text-center animate-in fade-in duration-500",
  {
    variants: {
      status: {
        empty: "text-stone-500 bg-stone-50/50 rounded-xl border border-dashed border-stone-200",
        error: "text-red-700 bg-red-50/50 rounded-xl border border-red-100",
        loading: "text-orange-600",
        partial: "text-amber-700 bg-amber-50 rounded-xl border border-amber-200",
      },
      size: { sm: "min-h-[120px] text-sm py-4", md: "min-h-[240px] text-base" }
    },
    defaultVariants: { status: "empty", size: "md" }
  }
);

interface UnifiedFeedbackStateProps extends VariantProps<typeof feedbackVariants> {
  title?: string;
  message?: string;
  action?: React.ReactNode;
}

export function UnifiedFeedbackState({ status, size, title, message, action, className }: UnifiedFeedbackStateProps & { className?: string }) {
  const Icon = status === 'error' ? AlertCircle :
               status === 'loading' ? Loader2 :
               status === 'partial' ? Info : FileQuestion;

  return (
    <div className={cn(feedbackVariants({ status, size }), className)}>
      <Icon className={cn("mb-3 w-8 h-8", status === 'loading' && "animate-spin opacity-80")} />
      {title && <h3 className="font-semibold text-stone-800 mb-1">{title}</h3>}
      {message && <p className="max-w-sm text-inherit opacity-80 leading-relaxed">{message}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
```

### 3.3 带交互反馈的工作区外壳 `WorkspaceShell.tsx`
集成 `react-resizable-panels`。关键在于 Splitter 把手的交互细节（Hit-box 的宽域处理）：

```tsx
// apps/web/src/app/components/layout/WorkspaceShell.tsx
import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";
import { cn } from "@/lib/utils";

interface WorkspaceShellProps {
  sidebar?: React.ReactNode;
  main: React.ReactNode;
  inspector?: React.ReactNode;
  layoutId: string;
}

const StyledResizeHandle = ({ id }: { id: string }) => (
  // 扩大感应区 (w-2)，但视觉居中一条线，hover 时加深
  <PanelResizeHandle
    id={id}
    className="relative flex w-2 items-center justify-center outline-none hover:bg-transparent data-[resize-handle-active]:bg-transparent group cursor-col-resize z-20"
  >
    <div className="w-[1px] h-full bg-stone-200 transition-colors duration-200 ease-out group-hover:bg-orange-400 group-hover:w-[2px] group-hover:shadow-[0_0_8px_rgba(234,88,12,0.3)] data-[resize-handle-active]:bg-orange-500 data-[resize-handle-active]:w-[2px]" />
  </PanelResizeHandle>
);

export function WorkspaceShell({ sidebar, main, inspector, layoutId }: WorkspaceShellProps) {
  return (
    <PanelGroup direction="horizontal" autoSaveId={`scholar-layout-${layoutId}`} className="h-full w-full bg-stone-50 text-stone-900">
      {sidebar && (
        <>
          <Panel defaultSize={20} minSize={15} maxSize={30} collapsible className="bg-stone-50/80">
            {sidebar}
          </Panel>
          <StyledResizeHandle id={`${layoutId}-handle-1`} />
        </>
      )}
      <Panel defaultSize={sidebar && inspector ? 50 : 70} minSize={40} className="bg-white shadow-sm ring-1 ring-stone-900/5 z-10 overflow-hidden relative">
        {main}
      </Panel>
      {inspector && (
        <>
          <StyledResizeHandle id={`${layoutId}-handle-2`} />
          <Panel defaultSize={30} minSize={20} className="bg-stone-50/80">
            {inspector}
          </Panel>
        </>
      )}
    </PanelGroup>
  );
}
```

## 4. 页面大扫除与接壳按序执行计划

### Task 1: 视觉原语、全站字体与左侧导航全局下发 (Day 1)
- [x] **路径**：`apps/web/src/styles/global.css` / `apps/web/src/styles/theme.css` / `apps/web/src/app/components/*`
- [x] **实施项**：
  - **全站字体优化**：全局设定优化的字体栈与基准行高，使正文更具学术阅读感。
  - **左侧导航精简**：重构公共 Left Sidebar，缩减主功能组垂直占位，首屏仅暴漏 2-3 个主要入口；多出项封装于可下滑滚动的局域 `ScrollArea` 中。
  - **基础组件收口**：完全删去老旧 `EmptyState.tsx` 引用。引入高交互细节的 `Button.tsx` (包含 `:active:scale` 和 `focus-visible` 细节)。
  - **弹窗/模态框优化**：对 Radix UI 的基础模态框 / Dialog / Dropdown Menu 添加统一阴影 `shadow-xl ring-1 ring-stone-900/5` 以及出现消失时的弹簧伸缩展开动画 `data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95`。

### Task 2: P0 - Dashboard (看板) 与 Search (搜阅层) 大面积重构 (Day 2)
- [x] **重构内容**：
  - `Dashboard`: 拆除非响应式和硬编码的 grid，移除临时假数据。将所有的文献图块组件改为具有 `group-hover:border-orange-500/30 transition-all` 规范的学术卡片。保证从导航到卡片没有生硬直角。
  - `SearchWorkspace`: 在打字进行搜索时，必须应用 `startTransition` 或防抖。旧的搜索结果在此期间不得被清空，而是施加 `opacity-60 grayscale-[20%]`，并在列表顶部加上加载提示，实现“不跳变式搜索刷新”。长文本如摘要需要强制采用 `max-w-prose` 和 `leading-relaxed`。

### Task 3: P0 - KnowledgeWorkspace 分离神级组件 (Day 3)
- [x] **重构内容**：
  - 肢解 `KnowledgeBaseList.tsx`（超 700 行）。
  - **交互体验**：将目录树的点击态加入 `bg-stone-200/50` 与左侧橙色 accent border，Hover 延时 50ms。右侧主列表空态必须映射至 `<UnifiedFeedbackState status="empty" message="暂无文档" />`。
  - 对接入 `WorkspaceShell`，右侧审查区域作为 Inspector 默认隐藏，在点击列表项后采用 `PanelGroup` API 编程式展开。

### Task 4: P1 - 阅读与聊天界面的极高信息密度打磨 (Day 4)
- [x] **重构内容**：
  - `Read.tsx`: 删除所有纯手写的鼠标坐标计算拉伸代码。剥去厚重的白色背景，将 Outline 面板与 PDF PDF.js / 文档视图，通过 `WorkspaceShell` 收容。
  - **阅读交互细节**：右侧高亮笔记应包含悬停时的 `cursor-pointer` 和背景轻微变暖 `hover:bg-amber-50/50 transition-colors` 交互。
  - `ChatWorkspaceV2`: AI 生成回复流式输出期间，对话框自动向上滚动的吸附须丝滑；流式文字渲染采用 `@chenglou/pretext` 或 `react-markdown` 中的最佳排版支持多断行，代码块和表格区域加装平滑横向滚动容器。

### Task 5: 边缘视图与整站 Walkthrough 修正 (Day 5)
- [x] **重构内容**：
  - 将 `Notes` 和 `Compare` 塞入标准壳。
  - 通过 MCP 或 Manual Review 进行整站截图验证：对比边框阴影、圆角曲率变体的一致性。
  - 使用 DevTools 把网络请求 Throttle 至 3G，查验延迟骨架屏的 `delayMs` 和加载占位符的防闪烁处理。
  - 把辅助功能 `prefers-reduced-motion` 模拟开启，查验过度动画是否优雅降级为淡入淡出。

## 5. 验收标准 (Definition of Done)

- [x] **交互平滑度**：绝无闪烁。模拟慢速网络时，搜索列表和分类卡片的过渡拥有 stale-while-revalidate 数据保留与局部骨架屏。
- [x] **排版一致性**：所有主被动交互按钮按下均具有收缩微动效。所有焦点的键盘导航具有无违和感的淡橙色 Focus Ring。
- [x] **可拉伸工作区**：`WorkspaceShell` 全局无死角平铺核心的 6 个大页面。分割线 hover 交互感应正常且拉拽不跨越限定边界 (minSize/maxSize 被严格尊重)。
- [x] **视觉减压**：消除了 God Pages 单文件，页面在设计语言上没有割裂，成功呈现统一的“偏暖纸张杂志式学术排版系统”。

## 6. Closeout Evidence (2026-05-11)

- 关键代码：`apps/web/src/app/components/layout/WorkspaceShell.tsx`、`apps/web/src/features/search/components/SearchWorkspace.tsx`、`apps/web/src/features/search/components/SearchResultsPanel.tsx`、`apps/web/src/hooks/useSearch.ts`、`apps/web/src/features/kb/components/KnowledgeWorkspaceShell.tsx`、`apps/web/src/features/read/components/ReadWorkspace.tsx`、`apps/web/src/features/chat/workspace/ChatWorkspaceLayout.tsx`、`apps/web/src/features/notes/components/NotesWorkspaceScreen.tsx`、`apps/web/src/app/pages/Compare.tsx`
- 回归测试：`cd apps/web && npm run type-check`
- 聚焦测试：`cd apps/web && npm run test:run -- src/features/kb/components/KnowledgeWorkspaceShell.test.tsx src/features/search/components/SearchResultsPanel.test.tsx src/hooks/useSearch.test.tsx src/features/chat/hooks/usePinnedBottom.test.tsx src/features/chat/components/message-feed/MessageFeed.test.tsx src/app/pages/Search.test.tsx src/features/chat/workspace/ChatWorkspaceV2.test.tsx`（7 files / 34 tests passed）
- 上游边界声明：Phase 4.0-4 已按“壳层 + 状态系统 + Typography/Density”范围完成；Phase 4.0-3（artifact contract closeout）仍维持 in-progress，不在本次 closeout 内宣称完成。
