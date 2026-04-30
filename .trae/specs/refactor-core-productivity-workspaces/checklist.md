# Checklist

- [ ] Chat 工作区已收敛为单一 canonical 实现，`ChatLegacy` 不再保留
- [ ] Chat 页面根组件只负责工作区壳层装配，`Composer` / `Feed` / `ContextSidebar` 已形成清晰边界
- [ ] Chat 的 streaming / SSE / 网络运行时逻辑已隔离到独立 hook 或 runtime 作用域
- [ ] Knowledge Base 详情工作区已收敛为单一 canonical 实现，`KnowledgeBaseDetailLegacy` 不再保留
- [ ] Knowledge Base 列表页的列表/卡片视图、筛选排序、批量操作、inspector 已拆分为清晰区域或控制器
- [ ] Knowledge Base 顶部工具栏的次级操作已收纳到标准 `DropdownMenu`
- [ ] Knowledge Base 的高风险大列表已接入虚拟化渲染，并在大量项目下避免明显卡顿
- [ ] Read 页面 durable preferences 已迁移到统一持久化层，刷新后可恢复
- [ ] Read 页面中的 PDF 导航、批注联动、linked note 同步等重副作用已拆入独立 controller/hook
- [ ] Notes 页面 durable preferences 已迁移到统一持久化层，页面根组件不再散落多处本地持久化副作用
- [ ] Notes 页面中的目录域、选择/过滤域、保存域已拆入独立 controller/hook
- [ ] Notes 删除操作不再依赖 hover，触屏与键盘用户可直接访问
- [ ] 四个核心工作区均符合“Layout Shell + State Controller + Presentational Sections + Durable Preferences Layer”的拆分协议
- [ ] 与本次变更相关的前端测试已更新并通过
- [ ] `cd apps/web && npm run type-check` 已通过
- [ ] 若拆分协议或页面边界规范发生变化，相关文档已同步更新
