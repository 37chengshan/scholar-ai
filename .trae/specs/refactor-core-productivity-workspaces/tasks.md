# Tasks

- [ ] Task 1: 收敛 Chat 工作区为单一 canonical 实现
  - [ ] SubTask 1.1: 盘点并删除 `ChatLegacy` 的兼容桥接与相关引用
  - [ ] SubTask 1.2: 将 `ChatWorkspaceV2` 拆分为布局壳层、`Composer`、`Feed`、`ContextSidebar` 三个主展示区
  - [ ] SubTask 1.3: 将 streaming / SSE / message 运行时编排收拢到独立 hook 或 runtime 作用域
  - [ ] SubTask 1.4: 为拆分后的 Chat 工作区补齐或更新单元测试

- [ ] Task 2: 重构 Knowledge Base 列表页与详情页边界
  - [ ] SubTask 2.1: 盘点并删除 `KnowledgeBaseDetailLegacy` 的兼容桥接与相关引用
  - [ ] SubTask 2.2: 将 `KnowledgeBaseList` 的列表/卡片切换、筛选排序、批量操作、工具栏次级操作、inspector 拆入独立区域或控制器
  - [ ] SubTask 2.3: 将顶部次级操作统一收纳到标准 `DropdownMenu` 交互模式
  - [ ] SubTask 2.4: 将 Knowledge Base 详情工作区壳层与各业务面板的 contract 明确化
  - [ ] SubTask 2.5: 为列表页与详情页重构补齐或更新测试

- [ ] Task 3: 为 Knowledge Base 大列表接入虚拟化渲染
  - [ ] SubTask 3.1: 识别知识库列表、论文列表、引用来源列表中的高风险大集合入口
  - [ ] SubTask 3.2: 选择并接入现有依赖中的虚拟化方案（优先复用 `react-window`）
  - [ ] SubTask 3.3: 在不破坏筛选、排序、布局切换的前提下完成可视区域渲染
  - [ ] SubTask 3.4: 为虚拟化行为补齐关键测试或验证用例

- [ ] Task 4: 抽离 Read 页面 durable preferences 与控制器层
  - [ ] SubTask 4.1: 将面板宽度、侧栏开闭、全屏状态、默认右侧面板等 durable preferences 从页面局部状态提炼到统一持久化层
  - [ ] SubTask 4.2: 将 PDF 导航、批注联动、linked note 同步、来源跳转等副作用拆入独立 hook/controller
  - [ ] SubTask 4.3: 确保刷新、跳转与重新进入时偏好恢复行为一致
  - [ ] SubTask 4.4: 为 Read 重构补齐或更新测试

- [ ] Task 5: 抽离 Notes 页面 durable preferences、目录域与保存域
  - [ ] SubTask 5.1: 将页面内 durable preferences 收敛到统一持久化层，减少散落的本地副作用
  - [ ] SubTask 5.2: 将文件夹目录、阅读摘要投影、选择与过滤逻辑拆入独立 hook/controller
  - [ ] SubTask 5.3: 保持 `useAutoSave` / IndexedDB 草稿恢复链路可用，并减少页面根组件的编排压力
  - [ ] SubTask 5.4: 移除“仅 Hover 时才能删除笔记”的交互，改为常驻次级操作
  - [ ] SubTask 5.5: 为 Notes 重构补齐或更新测试

- [ ] Task 6: 建立跨工作区的页面拆分与持久化约束
  - [ ] SubTask 6.1: 为 Chat、Knowledge Base、Read、Notes 统一明确 URL 状态、durable preferences、运行时瞬时状态、服务端资源状态的责任边界
  - [ ] SubTask 6.2: 复用现有 Zustand / Context / hooks 模式，避免再引入平行状态体系
  - [ ] SubTask 6.3: 在实现中收敛页面 root 的条件分支和副作用堆叠，确保工作区壳层仅负责布局与装配

- [ ] Task 7: 更新规范并完成验证
  - [ ] SubTask 7.1: 按实际落地结果更新 `docs/specs/design/frontend/DESIGN_SYSTEM.md`
  - [ ] SubTask 7.2: 若工作区边界有系统层变化，更新 `docs/specs/architecture/system-overview.md`
  - [ ] SubTask 7.3: 运行前端类型检查 `cd apps/web && npm run type-check`
  - [ ] SubTask 7.4: 运行与本次变更直接相关的测试，并修复失败项

# Task Dependencies

- Task 2 depends on Task 1 的拆分原则（两者可并行实现，但需遵循统一工作区边界）
- Task 3 depends on Task 2（Knowledge Base 边界稳定后再接入虚拟化风险更低）
- Task 4 与 Task 5 可并行
- Task 6 depends on Task 1, Task 2, Task 4, Task 5
- Task 7 depends on Task 1-6
