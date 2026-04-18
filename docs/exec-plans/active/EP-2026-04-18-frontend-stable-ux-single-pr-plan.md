---
phase: 0
wave: 1
depends_on: []
files_modified:
  - apps/web/src/hooks/useSearch.ts
  - apps/web/src/services/searchApi.ts
  - apps/web/src/features/search/hooks/useUnifiedSearch.ts
  - apps/web/src/features/search/components/SearchWorkspace.tsx
  - apps/web/src/features/search/components/SearchResultsPanel.tsx
  - apps/web/src/features/search/components/SearchPagination.tsx
  - apps/web/src/features/chat/workspace/ChatWorkspaceV2.tsx
  - apps/web/src/features/chat/components/session-sidebar/SessionSidebar.tsx
  - apps/web/src/features/chat/components/session-sidebar/SessionSidebar.test.tsx
  - apps/web/src/app/pages/KnowledgeBaseList.tsx
  - apps/web/e2e/search-pagination-stability.spec.ts
  - apps/web/e2e/chat-session-search.spec.ts
  - apps/web/package.json
autonomous: true
---

<objective>
在不改后端接口的前提下，单 PR 内完成 ScholarAI 前端“稳定可用优先”的体验加固：
1) 搜索分页稳定（不闪屏、可缓存、可取消、可预取）；
2) 会话搜索可用（真实筛选）；
3) 假能力止损（去除/禁用批量导出伪交互）；
4) 补齐关键浏览器 E2E 回归。
</objective>

<execution_waves>
Wave 1（基础设施/状态与请求层）
Wave 2（组件交互与视觉反馈层）
Wave 3（集成验证与测试门禁）
</execution_waves>

<task id="0-1-01">
<name>搜索请求层稳定化（缓存 + 取消 + 预取 + 保留旧数据）</name>
<read_first>
- apps/web/src/hooks/useSearch.ts
- apps/web/src/features/search/hooks/useUnifiedSearch.ts
- apps/web/src/services/searchApi.ts
- apps/web/src/lib/queryClient.ts
</read_first>
<action>
1. 将 useSearch 从 useEffect + setLoading 的整体替换模型迁移为 React Query 查询模型（useQuery）。
2. 查询键固定为 query + page + filters（sources/year/sortBy），保证分页缓存命中可重用。
3. 首次加载与翻页加载拆分为 isInitialLoading 与 isPageFetching 两个状态。
4. 使用 keepPreviousData（或等价 placeholderData）保留上一页结果，避免翻页空白。
5. 在当前页成功后 prefetch 下一页（next page），并在 query/filters 变化时取消旧请求。
6. 在 searchApi.unified 增加可选 signal 参数，并透传给 axios 请求（不改后端接口与路径）。
</action>
<acceptance_criteria>
- `apps/web/src/hooks/useSearch.ts` 包含 `useQuery(`。
- `apps/web/src/hooks/useSearch.ts` 包含 `keepPreviousData` 或 `placeholderData`。
- `apps/web/src/hooks/useSearch.ts` 包含 `prefetchQuery(`。
- `apps/web/src/hooks/useSearch.ts` 导出 `isInitialLoading` 与 `isPageFetching`。
- `apps/web/src/services/searchApi.ts` 的 `unified(` 支持可选 `signal` 参数并传入请求配置。
</acceptance_criteria>
</task>

<task id="0-1-02" depends_on="0-1-01">
<name>会话搜索状态接线与可测试过滤逻辑</name>
<read_first>
- apps/web/src/features/chat/components/session-sidebar/SessionSidebar.tsx
- apps/web/src/features/chat/workspace/ChatWorkspaceV2.tsx
- apps/web/src/app/hooks/useSessions.ts
- apps/web/src/features/chat/components/session-sidebar/SessionSidebar.test.tsx
</read_first>
<action>
1. 在 ChatWorkspaceV2 引入 sessionSearchQuery 状态，并基于 title + 最近消息数量文案做前端过滤（仅前端展示层）。
2. 向 SessionSidebar 透传 searchValue 与 onSearchChange；输入框受控并具备可访问名称。
3. 过滤后列表保持当前选中态与删除/切换行为不变。
4. 为空结果增加“无匹配会话”文案，不影响“无会话”文案。
</action>
<acceptance_criteria>
- `apps/web/src/features/chat/components/session-sidebar/SessionSidebar.tsx` 的输入框包含 `value=` 与 `onChange=`。
- `apps/web/src/features/chat/workspace/ChatWorkspaceV2.tsx` 包含 `sessionSearchQuery` 状态与 `filteredSessions` 计算。
- `apps/web/src/features/chat/workspace/ChatWorkspaceV2.tsx` 中 `SessionSidebar` 的 `sessions` 入参改为过滤结果。
- `apps/web/src/features/chat/components/session-sidebar/SessionSidebar.test.tsx` 新增会话搜索过滤用例。
</acceptance_criteria>
</task>

<task id="0-2-01" depends_on="0-1-01">
<name>搜索结果区防闪烁改造（组件层）</name>
<read_first>
- apps/web/src/features/search/components/SearchWorkspace.tsx
- apps/web/src/features/search/components/SearchResultsPanel.tsx
- apps/web/src/features/search/components/SearchPagination.tsx
</read_first>
<action>
1. SearchWorkspace 将 loading 拆分传参为 isInitialLoading / isPageFetching。
2. SearchResultsPanel 仅在 isInitialLoading 时显示全区加载；翻页时保留已有结果并显示局部顶部进度提示。
3. SearchPagination 在 isPageFetching 时仅禁用并显示按钮内 loading 态，不触发整块替换。
4. 保留当前视觉语言（字体、色板、间距），仅增强动效与反馈一致性，避免视觉跳变。
</action>
<acceptance_criteria>
- `apps/web/src/features/search/components/SearchResultsPanel.tsx` 不再使用 `if (loading) return ...` 的整块替换分支。
- `apps/web/src/features/search/components/SearchResultsPanel.tsx` 存在 `isInitialLoading` 与 `isPageFetching` 分支。
- `apps/web/src/features/search/components/SearchPagination.tsx` 在翻页请求时具备 `aria-busy` 或等价状态标记。
</acceptance_criteria>
</task>

<task id="0-2-02" depends_on="0-1-02">
<name>批量导出伪交互止损（稳定可用优先）</name>
<read_first>
- apps/web/src/app/pages/KnowledgeBaseList.tsx
- docs/reports/2026-04-18_前端体验优化_Roadmap.md
</read_first>
<action>
1. 去除“点击后仅提示未实现”的批量导出交互：将导出按钮设为 disabled 并标注“即将上线”，或在批量栏中隐藏导出入口（二选一）。
2. 保持批量删除完整可用，不改变现有 API 行为。
3. 删除“批量导出功能暂未完全实现”提示文案，避免伪可用感。
</action>
<acceptance_criteria>
- `apps/web/src/app/pages/KnowledgeBaseList.tsx` 不再包含字符串 `批量导出功能暂未完全实现`。
- 批量操作栏中导出按钮不可触发未实现 toast（通过 UI 禁用或隐藏实现）。
- 批量删除相关逻辑与按钮仍保留可用。
</acceptance_criteria>
</task>

<task id="0-3-01" depends_on="0-2-01">
<name>单元/集成测试补齐（分页稳定与会话搜索）</name>
<read_first>
- apps/web/src/features/chat/components/session-sidebar/SessionSidebar.test.tsx
- apps/web/src/app/pages/Search.test.tsx
- apps/web/src/features/search/__tests__/searchFlow.benchmark.test.ts
</read_first>
<action>
1. 为 SessionSidebar 增加输入筛选行为测试：输入关键字后仅渲染匹配会话。
2. 为 useSearch 增加分页稳定测试：翻页时保持上一页结果直到新页返回；快速切换时旧请求不覆盖新结果。
3. 为 SearchResultsPanel 增加渲染测试：isPageFetching 时结果仍在，且出现局部 loading 提示。
</action>
<acceptance_criteria>
- 新增或更新的单测文件包含 `session search`、`keep previous data`、`page fetching` 相关断言。
- `npm run test:run -- SessionSidebar` 可通过。
- `npm run test:run -- useSearch` 可通过。
</acceptance_criteria>
</task>

<task id="0-3-02" depends_on="0-2-01,0-2-02">
<name>浏览器 E2E 回归补齐并纳入脚本</name>
<read_first>
- apps/web/e2e/chat-critical.spec.ts
- apps/web/e2e/retrieval-critical.spec.ts
- apps/web/e2e/kb-critical.spec.ts
- apps/web/playwright.config.ts
- apps/web/package.json
</read_first>
<action>
1. 新增 e2e/search-pagination-stability.spec.ts：覆盖“输入检索词 -> 下一页 -> 上一页/再次翻页”，断言结果区持续可见且分页状态更新正确。
2. 新增 e2e/chat-session-search.spec.ts：创建多会话或利用已有会话，输入侧边栏搜索词，断言匹配与切换可用。
3. 将两条新用例纳入 `test:e2e` 与 `test:e2e:ci` 脚本，保持 Chromium 单项目执行策略。
</action>
<acceptance_criteria>
- `apps/web/e2e/search-pagination-stability.spec.ts` 文件存在并包含分页稳定断言。
- `apps/web/e2e/chat-session-search.spec.ts` 文件存在并包含会话筛选断言。
- `apps/web/package.json` 的 `test:e2e` 与 `test:e2e:ci` 包含上述两个 spec。
</acceptance_criteria>
</task>

<task id="0-3-03" depends_on="0-3-01,0-3-02">
<name>单 PR 验证与回滚锚点</name>
<read_first>
- apps/web/package.json
- apps/web/playwright.config.ts
- docs/reports/2026-04-18_前端体验优化_Roadmap.md
</read_first>
<action>
1. 执行 type-check、目标单测、目标 E2E；记录失败截图与 trace。
2. 回滚锚点定义：
   a) 若缓存改造引入结果错乱，回滚 task 0-1-01（保留组件层改造）；
   b) 若会话搜索引入选择错乱，回滚 task 0-1-02（保留搜索分页改造）；
   c) 若 E2E 不稳定，仅回滚新增 E2E 文件与脚本项，不回滚业务修复。
3. 输出 PR 验收说明：稳定性指标、视觉一致性说明、风险和已知限制。
</action>
<acceptance_criteria>
- `apps/web` 下 `npm run type-check` 通过。
- `apps/web` 下新增/变更单测通过。
- `apps/web` 下目标 E2E（至少 5 条 critical + 2 条新增）可执行并产出报告。
</acceptance_criteria>
</task>

<must_haves>
- 稳定可用优先于功能扩张：先消除伪交互与翻页闪烁，再考虑新增能力。
- 美观与性能并行：翻页过程保持视觉连续，不以“禁用动效”换取性能。
- 不改后端接口：仅改前端请求层与展示层，不新增后端 endpoint。
- E2E 回归覆盖新增关键路径：搜索分页稳定性、会话搜索可用性。
- 量化验收必须达成：
  1) 翻页交互中结果列表 DOM 不整块卸载；
  2) 已访问分页二次进入命中缓存并在 200ms 内呈现；
  3) 快速翻页/改查询不出现旧请求覆盖新结果；
  4) 会话搜索输入后 100ms 内完成前端过滤反馈；
  5) 不再出现“暂未完全实现”用户可见提示。
</must_haves>
