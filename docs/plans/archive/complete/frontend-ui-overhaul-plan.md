# Frontend UI Overhaul Plan — Chat 产品化 + KB/Read/Notes 页面打磨

> 分支: feat/frontend-ui-overhaul-20260420  
> 目标: Chat 为登录后首页 + Chat 体验产品级打磨 + KB/Read/Notes 全面改造  
> 原则: 保留 ScholarAI 杂志风格，不破坏 SSE 流式逻辑

---

## 一、路由与导航变更

### 1.1 登录后首页改为 Chat
- `Login.tsx`: `navigate("/dashboard")` → `navigate("/chat")`
- `routes.tsx`: Layout 下增加 `index` 重定向到 `/chat`
- `Layout.tsx`: 将 Chat 移到导航首位

### 1.2 导航文案统一
- EN: Overview→Dashboard, Knowledge→Knowledge Bases, Terminal→Chat
- ZH: 仪表盘→首页, 终端对话→AI 对话

---

## 二、Chat 页面全面改造

### 2.1 死码清理
- 删除 `ChatLegacy.tsx` (空壳)
- 删除 `ChatRunContainer.tsx` (空壳)
- 删除 `workspace/rollout.ts` (rollout 已完成, 100%)
- `ChatWorkspace.tsx` 直接渲染 `ChatWorkspaceV2`

### 2.2 SessionSidebar 升级
- 增加时间分组: 今天 / 昨天 / 本周 / 更早
- 会话条目宽度自适应, 文本截断优化
- 侧边栏可收起 (折叠到 48px 仅显示图标)
- 新建对话按钮更醒目

### 2.3 ComposerInput 升级
- 模式选择从 3 个按钮 → 单个 dropdown chip
- 输入框底部吸附优化
- 发送/停止状态切换无闪烁
- placeholder 文案改为自然语言提示

### 2.4 MessageFeed 升级
- User 消息: 右对齐 compact 气泡, 暖橙背景
- Assistant 消息: 左对齐全宽, 白底卡片
- 消息间距优化: 同角色 12px, 跨角色 20px
- 流式光标 blink 指示器
- Reasoning/Tools 默认折叠为 summary 行

### 2.5 ChatHeader 升级
- 简化: session 名称 + scope badge + 右侧 toggle
- 移除冗余的 Bot 图标

### 2.6 Layout 改动
- Chat 路由下移除 SVG noise texture overlay

---

## 三、KB 页面改造

### 3.1 KnowledgeBaseList 升级
- 页面标题文案: "知识库" → "我的知识库"
- 创建 KB 按钮: "创建" → "+ 新建知识库"
- 卡片设计: 增加 paper count badge, 更新时间更醒目
- 空状态: 更有引导性的 empty state
- 导入对话框文案校对: 统一为中文/英文对应

### 3.2 KnowledgeBaseDetail 升级
- 论文列表: 增加阅读进度 badge
- 导入论文 CTA 更醒目
- 右侧面板标签文案校对

---

## 四、Read 页面改造

### 4.1 工具栏升级
- 页码导航: 更紧凑, 快捷键提示
- 缩放控制: 数值显示
- 全屏: 快捷键 F

### 4.2 右侧面板升级
- 标签文案: 批注/AI总结/笔记 → 统一中文
- 标签顺序: 笔记优先 (用户最常用)
- AI 总结面板: 加载状态更友好

---

## 五、Notes 页面改造

### 5.1 文件夹树升级
- 文件夹图标更明显
- AI笔记标记更清晰
- 空文件夹提示文案

### 5.2 编辑器头部升级
- 标题可直接在顶部编辑
- 保存状态指示 (自动保存/已保存/未保存)
- 笔记分类 badge 显示

### 5.3 弹窗文案修复
- 删除确认: "确定" → "删除"
- 操作按钮统一风格

---

## 六、验收标准

- [ ] 登录后首页为 Chat
- [ ] Chat 侧边栏有时间分组
- [ ] Chat 消息 user/assistant 视觉区分清晰
- [ ] Chat 流式时有 blink 指示
- [ ] Reasoning/Tools 默认折叠
- [ ] KB 卡片信息密度合适
- [ ] Read 工具栏紧凑可用
- [ ] Notes 文案全部通顺
- [ ] 所有弹窗文案与项目一致
- [ ] 移动端基本可用
- [ ] type-check 通过
