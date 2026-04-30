# 核心生产力工作区瘦身与解耦 Spec

## Why

Chat、Knowledge Base、Read、Notes 是 ScholarAI 的核心生产力页面，但当前实现普遍存在页面根组件过厚、状态与副作用交织、Legacy/V2 双轨并存、大列表渲染缺乏保护等问题，导致维护成本高、回归风险大、交互稳定性差。

本变更旨在把这些页面从“可运行的巨石页面”重构为“可演进的工作区系统”：明确布局壳层、状态控制器、持久化偏好、流式运行时与展示区的边界，并清退重复实现。

## What Changes

- 删除 Chat 与 Knowledge Base Detail 中仅作兼容桥接的 Legacy 实现，收敛为单一 canonical 工作区实现
- 将 Chat 工作区强制拆分为 `Composer`、`Feed`、`ContextSidebar` 三个主展示区，并将 streaming/network 收发隔离到独立 hook/runtime 作用域
- 将 Knowledge Base 列表页与详情页职责拆开：列表/卡片视图、筛选排序、批量操作、右侧 inspector、详情工作区不再堆叠在单页巨石组件中
- 为 Knowledge Base 大列表与大规模引用来源渲染引入虚拟化策略，避免数百项渲染阻塞主线程
- 将 Read 与 Notes 的页面级“偏好状态”从局部 `useState` 提取到可持久化的全局或模块级状态层，统一管理面板宽度、侧栏开关、全屏状态、展示偏好等 durable preferences
- 移除 Notes 中“仅 Hover 时才能删除”的关键交互，改为常驻且可触屏、可访问的次级操作
- 为四个工作区建立统一的页面拆分与持久化约束：页面 root 不承载重副作用，URL 状态、持久化偏好、服务端资源、运行时瞬时状态分别归位
- 必要时更新前端设计规范，以反映巨石页面拆分协议、核心操作常驻、工作区壳层抽象与虚拟化阈值

## Impact

- Affected specs:
  - docs/specs/design/frontend/DESIGN_SYSTEM.md
  - docs/specs/architecture/system-overview.md
- Affected code:
  - apps/web/src/app/pages/Chat.tsx
  - apps/web/src/features/chat/workspace/ChatWorkspaceV2.tsx
  - apps/web/src/features/chat/components/ChatLegacy.tsx
  - apps/web/src/features/chat/hooks/
  - apps/web/src/features/chat/state/
  - apps/web/src/app/pages/KnowledgeBaseList.tsx
  - apps/web/src/app/pages/KnowledgeBaseDetail.tsx
  - apps/web/src/features/kb/components/KnowledgeBaseDetailV2.tsx
  - apps/web/src/features/kb/components/KnowledgeBaseDetailLegacy.tsx
  - apps/web/src/features/kb/components/KnowledgeWorkspaceShell.tsx
  - apps/web/src/features/kb/hooks/
  - apps/web/src/features/kb/state/
  - apps/web/src/app/pages/Read.tsx
  - apps/web/src/app/pages/Notes.tsx
  - apps/web/src/app/components/notes/
  - apps/web/src/app/hooks/useAutoSave.ts

## ADDED Requirements

### Requirement: Chat Workspace Modular Composition

系统 SHALL 将 Chat 工作区实现为可组合的模块化工作区，而不是单一巨石页面组件。

#### Scenario: Chat 工作区根组件装配

- **WHEN** 用户进入 Chat 页面
- **THEN** 页面根组件只负责装配工作区壳层、路由参数、主控制器与三个核心展示区
- **AND** 三个核心展示区至少包括 `Composer`、`Feed`、`ContextSidebar`
- **AND** 展示区之间仅通过明确 props、selector 或 view model 交互

#### Scenario: Streaming/network 职责隔离

- **WHEN** 用户发送消息并启动流式对话
- **THEN** SSE / streaming / message_id 绑定 / flush / cancel 等网络运行时逻辑必须落在独立 hook 或 runtime 作用域
- **AND** `ChatWorkspaceV2` 不得直接承担完整网络事件编排与 UI 渲染双重职责

#### Scenario: Chat 单一实现收敛

- **WHEN** 代码库提供 Chat 工作区实现
- **THEN** `ChatLegacy` 不再作为保留实现存在
- **AND** 仓库中只保留一套可被路由直接消费的 canonical Chat 工作区实现

### Requirement: Knowledge Base Workspace Performance Boundaries

系统 SHALL 为 Knowledge Base 的列表页与详情工作区建立清晰边界，并对大规模数据渲染提供性能保护。

#### Scenario: 列表页职责拆分

- **WHEN** 用户访问 Knowledge Base 列表页
- **THEN** 列表/卡片切换、筛选排序、批量操作、工具栏次级动作、右侧 inspector 应拆分为独立区域或控制器
- **AND** 页面根组件不应继续直接堆叠这些职责

#### Scenario: 大列表虚拟化

- **WHEN** 知识库列表、论文列表或引用来源列表一次性渲染大量项目
- **THEN** 系统必须使用虚拟化策略只渲染可视区域及必要 overscan 项
- **AND** 视图滚动、筛选、切换布局时不得因全量渲染导致明显主线程阻塞

#### Scenario: 工具栏视觉密度收敛

- **WHEN** 知识库列表页展示工具栏动作
- **THEN** 次级动作必须收纳到标准 `DropdownMenu`
- **AND** 顶部主工具栏只保留高频主操作、搜索、核心筛选与主要视图切换

#### Scenario: Knowledge Base 单一详情实现收敛

- **WHEN** 用户进入某个知识库详情页
- **THEN** 系统仅保留单一 canonical 详情工作区实现
- **AND** `KnowledgeBaseDetailLegacy` 不再作为保留实现存在

### Requirement: Durable Workspace Preferences

系统 SHALL 将 Read 与 Notes 中长期存在的用户偏好状态抽离为可持久化的 durable preferences，而不是散落在页面局部 `useState` 中。

#### Scenario: Read 偏好恢复

- **WHEN** 用户在 Read 页面调整右侧面板宽度、展开状态、全屏状态或默认面板
- **THEN** 系统将这些偏好写入统一的持久化状态层
- **AND** 用户刷新页面或重新进入时可恢复上次偏好

#### Scenario: Notes 偏好恢复

- **WHEN** 用户在 Notes 页面切换布局、侧栏开闭、筛选面板或其他 durable preferences
- **THEN** 系统将这些偏好写入统一的持久化状态层
- **AND** 页面组件不需要自行维护重复的 localStorage 读写副作用

#### Scenario: 偏好状态边界

- **WHEN** 系统管理工作区状态
- **THEN** URL 状态仅承载可分享或可刷新的导航语义
- **AND** 持久化偏好仅承载用户长期界面偏好
- **AND** 运行中瞬时状态不得误写为 durable preferences

### Requirement: Read and Notes Controller Separation

系统 SHALL 将 Read 与 Notes 页面中的重副作用和编排逻辑提炼为独立控制器层。

#### Scenario: Read 页面副作用拆分

- **WHEN** Read 页面处理 PDF 导航、批注联动、linked note 同步、来源跳转和偏好恢复
- **THEN** 这些逻辑应按领域拆入专用 hook/controller
- **AND** 页面根组件主要负责布局分区与控制器装配

#### Scenario: Notes 页面副作用拆分

- **WHEN** Notes 页面处理文件夹目录、阅读摘要投影、草稿同步、自动保存、选择与过滤联动
- **THEN** 这些逻辑应按 catalog、selection、filter、persistence 等边界拆入专用 hook/controller
- **AND** 页面根组件主要负责展示壳层与控制器装配

### Requirement: Core Actions Always Visible

系统 SHALL 保证主干路径与破坏性操作不依赖 hover 才可见。

#### Scenario: 删除笔记操作可见性

- **WHEN** 用户浏览 Notes 中的笔记列表或笔记详情
- **THEN** 删除操作必须以常驻但次级的方式可见
- **AND** 触屏用户与键盘用户无需 hover 即可访问该操作

#### Scenario: 其他核心操作可见性

- **WHEN** 工作区展示编辑、删除、查看详情、切换上下文等核心操作
- **THEN** 这些操作不得以 hover-only 作为唯一入口
- **AND** hover 只可作为视觉增强，而不是功能存在前提

## MODIFIED Requirements

### Requirement: Workspace Root Size and Responsibility

现有工作区页面 root 的要求修改为：

- 单一业务级 page root 不应继续承担网络流编排、偏好持久化、复杂筛选派生、大量条件分支渲染和布局细节 hardcode 的多重职责
- 当页面根组件规模或职责超过维护阈值时，必须拆分为：
  - Layout Shell
  - State Controller / Custom Hooks Layer
  - Presentational Sections
  - Durable Preferences Layer
- `Chat`、`Knowledge Base`、`Read`、`Notes` 属于强制执行该约束的核心工作区

### Requirement: Knowledge Base Rendering Strategy

现有 Knowledge Base 列表与详情页渲染要求修改为：

- 列表与卡片模式必须共享统一的数据控制层，但不在同一个巨石组件中交织全部渲染逻辑
- 大于阈值的数据集合必须接入虚拟化渲染，而不是继续全量 map 渲染
- 详情页中的 papers、evidence、runs、quick ask 等面板必须通过清晰 contract 接入 workspace shell

### Requirement: Local Persistence Discipline

现有页面级本地持久化要求修改为：

- 禁止在单个页面文件中散布多个独立的 localStorage 读写 effect 来承接 durable preferences
- 新的 durable preferences 必须集中到统一 store、context 或等价持久化层
- 仅保留与页面领域强相关、且已经通过抽象层暴露的持久化入口

## REMOVED Requirements

### Requirement: Legacy Compatibility Bridges for Productivity Workspaces

**Reason**: `ChatLegacy` 与 `KnowledgeBaseDetailLegacy` 仅作为历史迁移桥存在，继续保留会制造重复实现假象、增加维护面与回归风险。

**Migration**: 路由与调用方统一切换到 canonical workspace 实现；若测试仍依赖 bridge 名称，应同步更新测试入口与断言目标，而不是保留 bridge 文件。