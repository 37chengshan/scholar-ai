# ScholarAI 前端美观性与可用性全面审核报告（2026-04-22）

## 审核目标
- 覆盖主要页面，评估视觉一致性、信息层级、交互可用性、异常态体验、可访问性与可维护性。
- 输出可落地的分级修复方案（P0/P1/P2）。

## 审核范围
已覆盖页面：
- 首页
- 登录页
- 注册页
- 忘记密码页
- Chat 页
- 知识库页
- 搜索页
- Notes 页
- 设置页

未覆盖页面：
- 阅读页（需要具体 paperId 路由参数）
- 知识库详情页（需要具体 knowledge base id 路由参数）

## 截图证据
- [01 首页](logs/screenshots/ui-audit-2026-04-22/01-home.png)
- [03 登录页（未登录）](logs/screenshots/ui-audit-2026-04-22/03-login-unauth.png)
- [04 注册页](logs/screenshots/ui-audit-2026-04-22/04-register.png)
- [05 忘记密码页](logs/screenshots/ui-audit-2026-04-22/05-forgot-password.png)
- [06 Chat 页](logs/screenshots/ui-audit-2026-04-22/06-chat.png)
- [07 知识库页](logs/screenshots/ui-audit-2026-04-22/07-knowledge-bases.png)
- [08 搜索页](logs/screenshots/ui-audit-2026-04-22/08-search.png)
- [09 Notes 页错误截图](logs/screenshots/ui-audit-2026-04-22/09-notes-error.png)
- [10 设置页](logs/screenshots/ui-audit-2026-04-22/10-settings.png)

## 关键结论（先看）
- P0：Notes 页面可用性中断（白屏错误），必须优先修复。
- P1：登录/注册表单的可访问性与可读性不足，影响首次转化与键盘用户。
- P1：搜索页右侧信息密度和边缘元素表现不稳定，影响主任务聚焦。
- P2：首页叙事区与内容区节奏断层明显，首屏之后的信息连续性不足。
- P2：设置页左右三栏权重失衡，主操作区与诊断区视觉竞争。

## 详细问题清单（按严重级别）

### P0（阻断问题）
1) Notes 页面直接报错，无法使用
- 现象：出现 Unexpected Application Error，报错 useLocation() may be used only in the context of a <Router> component。
- 证据：见 [09 Notes 页错误截图](logs/screenshots/ui-audit-2026-04-22/09-notes-error.png)。
- 高概率根因：路由 hook 来源不一致。Notes 页面使用 react-router-dom 的 useSearchParams，而工程其他路由大量使用 react-router 包。
- 代码证据：
  - [Notes hook 导入](apps/web/src/app/pages/Notes.tsx#L13)
  - [Notes 中 useSearchParams 调用](apps/web/src/app/pages/Notes.tsx#L187)
  - [路由定义](apps/web/src/app/routes.tsx#L1)

修复建议：
- 统一路由库来源，优先全仓统一为 react-router-dom 或统一为 react-router（二选一，不混用）。
- Notes 页先做最小修复：与路由容器保持同源 hook 导入。
- 在顶层路由补充 errorElement，避免开发期原始栈追踪直接暴露给用户。

验收标准：
- 打开 /notes 不再报错。
- 能完成新建、筛选、编辑、删除笔记的完整闭环。

### P1（高优先级体验问题）
1) 登录/注册表单可访问性不足
- 现象：标签文字与占位符对比度偏低，弱视用户阅读成本高；label 与 input 未建立 htmlFor/id 关联，点击标签无法稳定聚焦输入框。
- 代码证据：
  - [Login 标签与输入](apps/web/src/app/pages/Login.tsx#L278)
  - [Login 输入 focus 样式](apps/web/src/app/pages/Login.tsx#L285)
  - [Register 标签与输入](apps/web/src/app/pages/Register.tsx#L197)
  - [Register 输入 focus 样式](apps/web/src/app/pages/Register.tsx#L204)
- 证据截图：
  - [03 登录页（未登录）](logs/screenshots/ui-audit-2026-04-22/03-login-unauth.png)
  - [04 注册页](logs/screenshots/ui-audit-2026-04-22/04-register.png)

修复建议：
- 为每个输入增加稳定 id/name/autocomplete，label 使用 htmlFor 关联。
- 增强 focus-visible 样式，避免仅靠细边框颜色变化。
- 提升输入 placeholder 与辅助文本对比度，保证低对比环境可读。

2) 搜索页右侧信息区干扰主任务
- 现象：主检索区和右侧分析区同时高密度展示，右侧有边缘元素抢注意力；空结果时主区价值密度低。
- 证据截图：
  - [08 搜索页](logs/screenshots/ui-audit-2026-04-22/08-search.png)
- 代码线索：
  - [Search Workspace 右侧 aside](apps/web/src/features/search/components/SearchWorkspace.tsx#L193)

修复建议：
- 空搜索态优先呈现“推荐检索词/最近主题/快捷模板”，减少大面积空白。
- 右侧分析区改为可折叠，默认收起或仅保留一条摘要带。
- 保留一个明确主 CTA（查询），其他次要操作降权。

### P2（中优先级视觉与信息架构问题）
1) 首页叙事节奏断层
- 现象：首屏视觉冲击强，但下游信息层（功能/技术/证明）在连续浏览路径上衔接弱，导致滚动后“信息真空感”。
- 证据截图：
  - [01 首页](logs/screenshots/ui-audit-2026-04-22/01-home.png)
- 代码线索：
  - [Landing 页结构](apps/web/src/app/pages/Landing.tsx#L68)

修复建议：
- 在首屏后增加“过渡锚点区”：3 条价值证据（速度、准确率、覆盖数据源）。
- 将功能区卡片间距压缩 10%-15%，提高信息连续性。
- 在每段结尾增加下一段的可见引导（箭头/目录高亮/滚动提示）。

2) 设置页三栏权重失衡
- 现象：左栏个人信息和右栏诊断都较重，中栏表单主任务视觉优势不足。
- 证据截图：
  - [10 设置页](logs/screenshots/ui-audit-2026-04-22/10-settings.png)

修复建议：
- 中栏提高纵向优先级：标题、分组、保存反馈固定在视觉主轴。
- 右栏诊断改弱化样式或折叠抽屉，默认只显示关键状态。

## 页面级审计摘要
- 首页：品牌风格鲜明，首屏完成度高；中后段信息节奏可继续优化。
- 登录页：视觉风格统一，转化链路清楚；无障碍与对比度需要加强。
- 注册页：信息完整；输入可读性与标签可点击性不足。
- 忘记密码：结构干净，主路径清晰；可补充成功态与错误态引导文案。
- Chat：左栏与主会话区组织清晰；右侧详情区在无选中消息时占位感偏强。
- 知识库：卡片体系稳定、信息层次较好；可再增强批量操作反馈。
- 搜索：检索入口明确；空态价值密度和侧栏干扰需要治理。
- Notes：当前不可用（P0）。
- 设置：模块全；主次层级需要再平衡。

## 解决方案（两周落地版本）

### 阶段一（D1-D2，先修阻断）
- 修复 Notes 路由 hook 同源问题。
- 为路由补充错误边界页，替代默认开发报错屏。
- 回归测试 /notes 核心流程（增删改查、筛选、关联论文）。

### 阶段二（D3-D5，高优先可用性）
- 登录/注册表单无障碍整改：label-htmlFor、id/name/autocomplete、focus-visible。
- 表单文本对比度与状态反馈整改（错误、加载、成功提示）。
- 搜索页空态与侧栏收敛：默认收起侧栏，主任务优先。

### 阶段三（D6-D10，视觉与结构优化）
- 首页信息连续性优化：过渡证据区 + 滚动引导。
- 设置页三栏权重重排，中栏主任务优先。
- 增加统一的页面级可用性基线检查（空态、错误态、加载态一致）。

## 建议验收清单
- Notes 页可稳定打开并可完整编辑。
- 登录/注册支持键盘全流程，焦点可见，标签可点击。
- 搜索页在空态下也有明确下一步动作，右侧面板不抢主任务焦点。
- 首页从首屏到功能区的连续阅读路径无“空窗感”。
- 设置页用户首次进入 5 秒内可定位主操作入口（修改资料并保存）。

## 风险与说明
- 本次为可视化与交互审计，未包含性能压测与跨浏览器矩阵完整回归。
- 阅读页和知识库详情页需补充具体 id 才能完成同粒度截图审计。
