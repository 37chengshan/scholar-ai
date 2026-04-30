# Chat 页面深度改造计划

> 参考 ChatGPT 页面设计，保留 ScholarAI 学术暖色调设计风格
> 创建日期: 2026-04-20

---

## 一、改造目标

将 Chat 页面从当前「功能完整但视觉一般」升级为「ChatGPT 级别的交互体验」，同时保留 ScholarAI 的学术品牌调性（暖色调、Serif 标题、纸质质感）。

### 核心原则
1. **ChatGPT 的简洁交互** — 去除多余边框、减少视觉噪音
2. **ScholarAI 的学术气质** — 保留暖色调、Serif 字体、品牌橙色
3. **信息密度优化** — 消息区域最大化、辅助元素按需展示
4. **流式体验提升** — 更流畅的打字动画、更优雅的状态过渡

---

## 二、现状分析

### 当前问题
| 问题 | 描述 |
|------|------|
| 消息气泡过重 | AI 和用户消息都用圆角边框 + 阴影包裹，视觉密度高 |
| 头像占空间 | 每条消息都有 36px 圆形头像，像早期聊天 UI |
| 空状态单调 | 只有图标 + 标题 + 4 个建议卡片，没有品牌感和引导性 |
| 输入框不突出 | 输入区和页面融为一体，缺少「焦点」感 |
| 侧边栏过宽 | 252px 占过多水平空间，session 列表样式朴素 |
| Token 信息隐藏 | hover 才可见，且样式生硬 |
| 代码/Markdown 不渲染 | 消息内容只做 whitespace-pre-wrap，没有 Markdown 渲染 |

---

## 三、改造方案

### Phase 1: 消息气泡重设计（Message Bubble Redesign）

**参考**: ChatGPT 的「无气泡」AI 消息 + 紧凑用户消息

#### 变更清单

1. **AI 消息 — 去掉气泡边框**
   - 移除 `border`, `shadow-sm`, `bg-card/95`
   - 改为纯文本 + 左侧细竖线品牌色指示器（4px 宽 primary 色条）
   - 内容区域：直接渲染，无边框包裹
   - 头部标签（AI + 时间戳）保留但更精简

2. **用户消息 — 轻量胶囊气泡**
   - 保留右对齐和 `bg-primary` 背景
   - 圆角改为 `rounded-2xl rounded-br-md`（右下角小圆角，模仿微信/iMessage）
   - 移除用户头像，右侧只保留气泡
   - 最大宽度改为 `max-w-[75%]` 而非 `max-w-[min(44rem,100%)]`

3. **头像系统简化**
   - AI 消息：保留小头像（24px），使用 ScholarAI 品牌 logo 图标
   - 用户消息：完全移除头像
   - 头像与消息名称合并到一行

4. **消息间距优化**
   - 同角色连续消息：间距 `gap-1`（4px）
   - 不同角色切换：间距 `gap-6`（24px）
   - 时间戳只在角色切换或超过 5 分钟时显示

**涉及文件**: `MessageFeed.tsx`

---

### Phase 2: 输入区域升级（Composer Redesign）

**参考**: ChatGPT 的浮动输入框 + 附件按钮

#### 变更清单

1. **浮动输入框**
   - 输入框脱离底部固定位置，改为「浮动居中」
   - 背景：`bg-white` 带 `shadow-lg` 和 `ring-1 ring-black/5`
   - 圆角：`rounded-2xl`（更圆润）
   - 底部留 `pb-4` 安全区

2. **输入框内部布局**
   - 多行文本域不变，但增加 `min-h-[52px]`
   - 发送按钮移到输入框右下角内部（如 ChatGPT）
   - 发送按钮样式：圆形，`bg-primary` 
   - 新增附件按钮（暂为 placeholder，不实现功能）

3. **模式选择器重设计**
   - 移到输入框上方或左下角
   - 改为胶囊标签组（SegmentedControl）而非下拉菜单
   - 三种模式用小圆点颜色区分

4. **Typing indicator**
   - 流式响应时输入框显示「AI 正在思考...」
   - 输入框左下角显示当前模式标签

**涉及文件**: `ComposerInput.tsx`

---

### Phase 3: 空状态体验升级（Empty State Enhancement）

**参考**: ChatGPT 的品牌化空状态 + 能力展示

#### 变更清单

1. **品牌 Hero 区**
   - 更大的品牌 Logo（48px → 64px）
   - 渐变色背景光环效果
   - 标题改用 Serif 字体，更大更有学术感
   - 副标题展示 ScholarAI 的核心能力（论文分析、知识检索、深度推理）

2. **建议提示卡片升级**
   - 从 2x2 网格改为「垂直滚动列表 + 分类标签」
   - 每个提示更详细，带图标 + 标题 + 描述
   - 增加更多提示（6-8 个），按场景分类：
     - 📄 论文分析
     - 🔍 知识检索
     - 💡 创意思考
     - 📊 数据解读
   - 悬停动画：轻微上浮 + 左边框色条

3. **快捷操作区**
   - 底部增加「上传论文」快捷入口
   - 显示最近打开的论文/知识库快捷访问

**涉及文件**: `ChatEmptyState.tsx`

---

### Phase 4: 侧边栏优化（Session Sidebar Polish）

**参考**: ChatGPT 侧边栏的简洁分组 + 悬浮操作

#### 变更清单

1. **侧边栏宽度和过渡**
   - 展开宽度：252px → 260px
   - 折叠宽度保持 48px icon rail
   - 展开/折叠增加 `transition-all duration-200`
   - 移动端：overlay 模式（覆盖在内容上方）

2. **Session 列表项重设计**
   - 移除消息计数 badge
   - 每个 session 显示：标题（单行截断）+ 最后消息预览（单行浅色）
   - 当前选中项：左侧 3px primary 色条 + 浅橙色背景
   - 悬停时右侧出现「删除」图标（小 X）
   - 双行布局：标题 + 预览文字

3. **分组标题样式**
   - 更小的分组标签（10px uppercase tracking-widest）
   - 分组之间加 1px 分割线

4. **新建会话按钮**
   - 移到侧边栏顶部（如 ChatGPT 的 + 按钮）
   - 圆角按钮 + 图标
   - 带 tooltip

**涉及文件**: `SessionSidebar.tsx`

---

### Phase 5: Markdown 渲染支持

**参考**: ChatGPT 的完整 Markdown 渲染

#### 变更清单

1. **引入 Markdown 渲染器**
   - 使用 `react-markdown` + `remark-gfm` + `rehype-highlight`
   - 支持：标题、列表、粗体/斜体、代码块、行内代码、表格、引用
   - 代码块：带语言标识 + 复制按钮 + JetBrains Mono 字体

2. **AI 消息内容渲染管线**
   - `whitespace-pre-wrap` 替换为 Markdown 渲染
   - 流式输出保持逐字渲染效果
   - 代码块渲染带语法高亮

3. **消息操作栏**
   - 每条 AI 消息底部增加：复制、重新生成（placeholder）
   - 悬停时才显示，`opacity-0 group-hover:opacity-100`

**涉及文件**: `MessageFeed.tsx`, 新增 `MarkdownRenderer.tsx`

---

### Phase 6: 交互细节打磨

#### 变更清单

1. **流式动画优化**
   - 光标闪烁改为更柔和的动画（`animate-pulse` → 自定义 ease-in-out）
   - 消息出现使用 `motion/react` 的 fade+slide 动画
   - 工具调用状态指示器优化（旋转 → 脉冲 → 完成打勾）

2. **快捷键支持**
   - Enter 发送（已有）
   - ⌘/Ctrl + Shift + S：新建会话
   - ⌘/Ctrl + K：快速搜索会话
   - Escape：关闭侧边栏

3. **自动滚动优化**
   - 新消息到达时，如果用户在底部 → 平滑滚动到底
   - 用户手动上滚 → 底部出现「回到最新」按钮
   - 按钮样式：圆形 + 向下箭头 + 未读消息数

---

## 四、执行顺序

| 优先级 | Phase | 影响范围 | 复杂度 |
|--------|-------|---------|--------|
| P0 | Phase 1: 消息气泡重设计 | MessageFeed.tsx | 中 |
| P0 | Phase 2: 输入区域升级 | ComposerInput.tsx | 中 |
| P1 | Phase 3: 空状态升级 | ChatEmptyState.tsx | 低 |
| P1 | Phase 4: 侧边栏优化 | SessionSidebar.tsx | 中 |
| P2 | Phase 5: Markdown 渲染 | MessageFeed.tsx + 新文件 | 高 |
| P2 | Phase 6: 交互打磨 | 多文件 | 中 |

**本次执行**: Phase 1-4（核心视觉改造）
**后续迭代**: Phase 5-6（功能增强）

---

## 五、设计约束

1. **不修改数据流/状态管理** — 只改视觉层，hooks 和 store 不动
2. **不修改 SSE 通信逻辑** — 流式数据处理逻辑完全不变
3. **保持 Props 接口兼容** — 组件 Props 接口只增不删
4. **保持测试通过** — 改完后所有测试必须通过
5. **保留品牌色系** — primary (#d35400)、background (#fdfaf6)、serif 字体
6. **响应式** — 移动端至少不崩溃，桌面端优先

---

## 六、验收标准

- [ ] AI 消息无气泡、有品牌色指示器
- [ ] 用户消息紧凑胶囊气泡
- [ ] 输入框浮动居中、发送按钮在框内
- [ ] 模式选择器改为胶囊标签组
- [ ] 空状态有品牌感、建议提示分类展示
- [ ] 侧边栏 session 双行布局
- [ ] 流式输出顺畅、光标动画柔和
- [ ] 47 个测试全部通过
- [ ] TypeScript 编译无错误
