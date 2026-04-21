# ScholarAI 首页与内部工作台编辑杂志风统一改造计划

> 状态：proposed  
> 日期：2026-04-21  
> 适用范围：`apps/web`  
> 目标主题：Landing 与内部工作台统一采用 editorial magazine 风格，不再出现多套视觉语言并存

## 1. 计划目标

本计划用于把 ScholarAI 前端从“首页一套风格、内部一套风格、局部再拼第三套风格”的状态，收敛为一套统一的编辑杂志风产品界面。

本计划要解决的不是单页美化，而是以下四个核心问题：

1. 首页与内部页面品牌语言不一致。
2. Chat、Search、Knowledge Base、Settings 的视觉层级和排版口径不一致。
3. 全局 token 未真正成为唯一真源，存在大量硬编码颜色和局部自定义语义。
4. 编辑杂志风只停留在零散 serif、paper texture、暖橙 accent，没有变成系统化 UI。

最终目标是形成一套可以覆盖首页、导航壳层、工作台、内容卡片、数据侧栏、表单和空状态的统一视觉系统。

## 2. 北极星体验

### 2.1 用户应该感受到什么

1. 打开首页时，看到的是“研究工作台品牌”，不是通用 AI SaaS 首页。
2. 进入 Chat、Search、Knowledge Base 后，仍然能明显感知这是同一个产品，而不是切到了另一套站点。
3. 信息密度高，但不乱；像读一份设计克制、层级清楚的研究刊物，而不是看一堆通用 dashboard 卡片。
4. 视觉上有记忆点，但交互上不过度装饰，始终以可读性和任务完成为先。

### 2.2 成功后的产品气质

- 学术感：不是靠冷蓝科技色，而是靠字体、边线、留白、文案密度和证据排布。
- 编辑感：版面像杂志，不像后台模板。
- 工具感：虽然有 editorial 风格，但主任务路径依然清晰高效。
- 一致性：品牌、工作台、结果页、详情页属于同一系统。

## 3. 当前问题基线

基于现有代码审视，当前主要问题如下。

### 3.1 视觉语言断裂

1. 首页 `Landing.tsx` 采用 `teal/emerald` 冷色渐变与科技感 CTA。
2. 全局主题 `theme.css` 使用暖橙 `#d35400`、纸张底 `#fdfaf6` 和 editorial 字体。
3. 内部页面大量使用暖纸风、serif 标题、规则线，但首页没有延续这套语言。
4. 移动端导航、认证页、局部组件还存在硬编码色值。

### 3.2 编辑杂志风只停留在碎片层

1. `font-serif` 使用零散，没有统一的标题等级体系。
2. 边线、卡片、paper shadow、纹理、徽标、章节标题没有形成稳定模式。
3. 小号 uppercase 标签过多，导致“有风格但不耐读”。
4. 很多页面像“暖色 dashboard”，而不是“杂志化研究工作台”。

### 3.3 壳层与内容关系没有统一

1. Layout 顶栏偏紧、偏功能栏，但首页是品牌展示感。
2. Search 是三栏结构，Chat 是工作台结构，KB 是工具条结构，但三者的面板语法不一致。
3. 结果页与会话页都包含侧栏和卡片，但边界、圆角、标题、空状态、交互反馈口径不同。

### 3.4 视觉优先级错位

1. 一些次要信息块被做得和主内容一样重。
2. 很多小标签、描边、阴影都在争夺注意力。
3. 部分装饰性动效与品牌表达不一致，也没有 reduced-motion 收口。

## 4. 设计总原则

### 4.1 一套系统，不做两套品牌

Landing 与内部工作台必须共用同一套语义 token、排版等级、按钮逻辑、装饰策略。

允许差异：

- 首页更强调叙事和品牌。
- 内页更强调任务和信息效率。

不允许差异：

- 品牌主色不同。
- 主字体策略不同。
- 主卡片语言不同。
- 页面气质一个偏科技 startup、一个偏暖纸 editorial。

### 4.2 编辑杂志风不等于复古 UI

保留：

- serif 标题
- sans 正文
- warm paper 底色
- 细规则线
- 编排感留白
- 章节感标题
- 轻度纸面质感

避免：

- 过度拟物纸张效果
- 大面积装饰噪点
- 厚重边框和过多 box
- 假装“报纸排版”但牺牲可读性

### 4.3 任务优先，品牌服务于任务

编辑风只能提升理解和品牌识别，不能干扰以下核心路径：

1. 开始研究
2. 搜索论文
3. 导入知识库
4. 发起问答
5. 阅读证据
6. 回看历史会话

### 4.4 统一使用语义 token

不再允许页面自己定义一套 `teal`、另一套 `orange`、第三套灰度系统。

后续所有新样式必须优先使用：

- `--color-background`
- `--color-card`
- `--color-paper-*`
- `--color-foreground`
- `--color-muted-foreground`
- `--color-primary`
- `--color-secondary`
- `--color-rule`
- `--shadow-paper*`
- `--font-serif`
- `--font-sans`
- `--font-mono`

## 5. 目标视觉系统

## 5.1 配色策略

主方向统一为暖纸底 + 墨色正文 + 暖橙强调。

### 核心角色

- Background：温暖纸白，作为所有页面底色基线。
- Surface：白色或浅纸色，用于内容承载。
- Ink：深褐黑正文，用于标题与主体阅读。
- Accent：暖橙，用于 CTA、激活态、进度强调、关键链接。
- Support Accent：深绿或暗青，仅用于成功/完成/证据可信，不能演变为第二主品牌色。

### 明确禁止

1. Landing 单独使用 `teal/emerald` 作为品牌主轴。
2. 页面局部直接写 `#d35400`、`#fdfaf6`、`#f4ece1` 作为组件私有值。
3. 新增无语义归属的彩色 gradient 作为主要视觉语言。

## 5.2 排版体系

### 标题字体

- 使用 `--font-serif`。
- 场景：Hero、区块标题、页面标题、关键卡片标题、空状态标题。

### 正文字体

- 使用 `--font-sans`。
- 场景：正文、说明、表单、导航、按钮、消息体、结果摘要。

### 等级策略

- H1：品牌/页面主标题，serif，紧 tracking，允许更大字号。
- H2：页面区块标题，serif。
- H3：卡片/模块标题，serif 或较强 sans，按场景决定。
- Label：功能标签，sans，减少全大写滥用。
- Meta：作者、时间、状态、计数，mono 或小号 sans。

### 排版约束

1. 10px 以下的大写标签仅保留在极少数 section kicker。
2. 正文区默认不使用 serif，尤其是 Chat 消息、搜索摘要、表单说明。
3. 标题与内容的垂直节奏要统一，不再每页自己决定密度。

## 5.3 间距与版面

### 统一页面骨架

- 顶部导航高度统一。
- 内容容器使用固定 max width 逻辑。
- 区块之间采用更明显的垂直节奏。
- 卡片内部留白必须形成 3 档：紧凑 / 标准 / 宽松。

### 杂志式编排策略

- 首页：大块面 + 章节感切分 + 明确叙事顺序。
- 内页：主内容列明确，侧栏是注释列，不与主区竞争。
- 数据块：像“边注”和“引文框”，不要做成大面积花哨仪表盘。

## 5.4 表面与边界

表面语言统一为：

1. 纸面卡片
2. 轻规则线
3. 克制阴影
4. 清晰边界

具体要求：

- 常规卡片优先 `paper + rule + shadow-paper`
- hover 只做轻微边线/阴影变化
- 尽量避免大圆角糖果卡片
- Chat/Search/KB 的面板边界形式要统一

## 5.5 动效

动效原则是“翻页感、揭示感、聚焦感”，而不是“漂浮科技感”。

建议：

1. 首页保留轻量 reveal。
2. 内页只保留必要过渡，不做大位移入场。
3. 统一 reduced motion 策略。
4. 面板展开优先高度/透明度变化，不做大幅横移。

## 6. 页面级改造策略

## 6.1 Landing

### 目标

把首页从“冷色 AI 产品宣传页”改成“ScholarAI 编辑杂志式研究工作台首页”。

### 当前问题

1. 颜色使用与内部不统一。
2. Hero 更像通用 SaaS 文案区，而不是研究工作台品牌入口。
3. 功能区块虽清晰，但风格偏 startup 卡片。

### 改造方向

1. 去掉 teal/emerald 主导色，统一切回 paper + ink + warm accent。
2. Hero 使用更强 editorial 编排：
   - 左右或上下错层排版
   - serif 主标题
   - 小号 kicker
   - 一段高度凝练的定位文案
   - 一个主 CTA，一个次 CTA
3. 加入更明确的“研究工作台感”内容：
   - Scope
   - Evidence
   - Recovery
   - Structured answer
4. Stats 从“营销数字条”改成“编辑边注式事实条”。
5. Features 从彩色卡片改为更克制的 paper panels。
6. CTA 区块改成“期刊封底式收束”，而不是深色科技块。

### 主要落点文件

- `apps/web/src/app/pages/Landing.tsx`
- `apps/web/src/app/components/landing/*`
- `apps/web/src/styles/theme.css`
- `apps/web/src/styles/global.css`

## 6.2 全局壳层 Layout

### 目标

让进入内部页面后的第一层体验，与 Landing 明显属于同一品牌系统。

### 当前问题

1. 顶栏过于紧凑，像工具导航，不像编辑工作台 masthead。
2. 移动端菜单和桌面端导航风格不完全一致。
3. 全局噪点纹理策略不清晰。

### 改造方向

1. 顶栏改为 editorial masthead 风格：
   - logo 更稳
   - 一级导航更清晰
   - 激活态不再只靠填充色块
   - 允许更明显的底部规则线
2. 用户区与设置区减少“控件拼接感”。
3. 移动端抽屉也使用同一纸面语言，不再写硬编码色。
4. 全局纹理降级为背景气氛层，只在非主阅读区轻度使用。

### 主要落点文件

- `apps/web/src/app/components/Layout.tsx`
- `apps/web/src/app/components/landing/Logo.tsx`
- `apps/web/src/styles/theme.css`
- `apps/web/src/styles/global.css`

## 6.3 Chat 工作台

### 目标

把 Chat 做成“研究对话编辑台”，而不是“暖色聊天应用”。

### 当前问题

1. 结构已接近工作台，但面板语言不统一。
2. 输入区、会话侧栏、顶部栏、右栏各说各话。
3. 杂志风元素没有明确职责，导致局部只有“加一点 serif”。

### 改造方向

1. 中央消息区保持最高纯度和最高可读性。
2. 会话侧栏做成“档案列”：
   - 时间分组更像期刊归档
   - 当前会话高亮更克制
   - 删除按钮默认不抢戏
3. 顶栏做成“当前研究页眉”：
   - 标题更稳定
   - 右侧详情开关更像边注切换
4. 输入区做成“编辑台底栏”：
   - 更像写作/研究输入器
   - 模式选择合并为更克制的 dropdown
   - 色点语义统一，不再引入额外品牌色
5. 右侧面板做成“边注列 / evidence column”：
   - 用规则线和分组标题组织
   - 默认信息密度更克制
6. 消息卡片、引用、工具调用、思考过程统一风格：
   - 强调阅读顺序
   - 减少工程味 telemetry 视觉

### 主要落点文件

- `apps/web/src/features/chat/workspace/ChatWorkspaceV2.tsx`
- `apps/web/src/features/chat/components/ChatHeader.tsx`
- `apps/web/src/features/chat/components/session-sidebar/SessionSidebar.tsx`
- `apps/web/src/features/chat/components/composer-input/ComposerInput.tsx`
- `apps/web/src/features/chat/components/ChatRightPanel.tsx`
- `apps/web/src/features/chat/components/message-feed/*`
- `apps/web/src/features/chat/components/workbench/*`
- `apps/web/src/app/components/ChatMessageCard.tsx`
- `apps/web/src/app/components/ExpandableCitation.tsx`
- `apps/web/src/app/components/ToolCallCard.tsx`

## 6.4 Search 工作台

### 目标

把 Search 做成“研究发现台 + 注释侧栏”，而不是普通三栏 dashboard。

### 当前问题

1. 三栏结构基础是对的，但视觉语法和 Chat 不统一。
2. 右侧 analysis 更像演示区，不像编辑批注区。
3. 小字和大写标签偏多，阅读负担偏高。

### 改造方向

1. 左栏做成“来源目录列”。
2. 中央结果列做成“论文版心”：
   - 结果列表是主阅读区
   - 分页、筛选、导入动作轻但清晰
3. 右栏降级为“研究边注列”：
   - 只保留真正帮助判断的内容
   - 弱化装饰性图块
4. 卡片与摘要统一成 editorial abstract 风格。
5. Search 与 Chat 的壳层、侧栏标题、边线、卡片语言对齐。

### 主要落点文件

- `apps/web/src/features/search/components/SearchWorkspace.tsx`
- `apps/web/src/features/search/components/SearchSidebar.tsx`
- `apps/web/src/features/search/components/SearchToolbar.tsx`
- `apps/web/src/features/search/components/SearchResultsPanel.tsx`
- `apps/web/src/features/search/components/SearchPagination.tsx`
- `apps/web/src/app/components/SearchResultCard.tsx`
- `apps/web/src/app/components/AuthorResultCard.tsx`

## 6.5 Knowledge Base

### 目标

把 KB 做成“研究资料库目录页”，而不是“功能工具条 + 卡片拼盘”。

### 当前问题

1. 顶部工具区过重。
2. 页面上同时出现过多操作元素。
3. 杂志风存在，但主要是暖色和 serif，缺少真正的编排秩序。

### 改造方向

1. 页面上方建立“资料库页眉”：
   - 标题
   - 简短状态信息
   - 主操作
2. 搜索、标签、排序、视图切换分层，不再全部同级抢注意力。
3. 存储统计做成次级信息条，而不是和主操作平级。
4. 卡片视图与列表视图共用同一 editorial card 语法。

### 主要落点文件

- `apps/web/src/app/pages/KnowledgeBaseList.tsx`
- `apps/web/src/app/components/KnowledgeBaseCard.tsx`
- `apps/web/src/app/components/BatchActionBar.tsx`
- `apps/web/src/app/components/EmptyState.tsx`
- `apps/web/src/features/kb/components/*`

## 6.6 Settings / Auth / Notes / Read

### 目标

补齐尾部页面，保证不是只有主链路统一，其它页面仍旧脱节。

### 改造方向

1. Auth 页与首页、内部页共用同一品牌语言。
2. Settings 从“配置页”升级为“账户与偏好编务页”。
3. Read 页面强调阅读版面，不要被工具边框包围。
4. Notes 页面统一边注与主稿关系。

### 主要落点文件

- `apps/web/src/app/pages/Login.tsx`
- `apps/web/src/app/pages/Register.tsx`
- `apps/web/src/app/pages/ForgotPassword.tsx`
- `apps/web/src/app/pages/ResetPassword.tsx`
- `apps/web/src/app/pages/Settings.tsx`
- `apps/web/src/app/pages/Read.tsx`
- `apps/web/src/app/pages/Notes.tsx`

## 7. 组件与设计系统改造项

## 7.1 Token 真源收口

第一优先级不是改页面，而是先收口 token。

### 必做项

1. 在 `theme.css` 中定义完整 editorial token。
2. 去掉页面级硬编码主色和背景色。
3. 明确以下语义层：
   - page background
   - paper surface
   - elevated surface
   - rules
   - accent
   - status
   - shadows

## 7.2 Typography 工具层

建议补一层可复用的 typography class 或约定，例如：

- `.editorial-kicker`
- `.editorial-title-xl`
- `.editorial-title-lg`
- `.editorial-meta`
- `.editorial-note`
- `.editorial-rule-heading`

目的不是新建庞大 CSS 体系，而是避免各页面继续手写零散字号和 tracking。

## 7.3 Card / Panel 语法统一

建议抽象 3 类容器语法：

1. `EditorialPanel`
2. `EditorialCard`
3. `EditorialSidebarSection`

至少在样式和 class 规范上统一以下属性：

- background
- border
- radius
- shadow
- heading
- hover
- active

## 7.4 空状态与说明性组件统一

空状态是 editorial 风格最容易建立品牌感的位置，建议统一：

1. 空状态标题
2. 描述文案
3. 插图线条
4. CTA 按钮
5. 次级说明

主要涉及：

- `EmptyState.tsx`
- Chat empty state
- Search empty state
- KB empty state

## 7.5 图标与徽记

继续使用 Lucide，但建立统一规则：

1. 图标默认尺寸统一。
2. 标签前图标仅在必要时出现。
3. 不用 emoji。
4. 状态点色值也走 token。

## 8. 实施波次

## Wave 0：视觉冻结与资产盘点

### 目标

先冻结“要统一成什么”，避免边改边漂移。

### 任务

1. 输出 editorial token 表。
2. 列出现有硬编码颜色和不一致字体用法。
3. 确认 Landing、Layout、Chat、Search、KB 作为第一批改造面。
4. 确认不再新增第二套颜色方向。

### 产物

- 本计划文档
- token mapping 清单

## Wave 1：全局 token 与骨架统一

### 目标

先解决“不是同一产品”的问题。

### 任务

1. 重构 `theme.css`。
2. 调整 `global.css` 的 focus、scrollbar、动效策略。
3. 改造 `Layout.tsx` 和 `Logo.tsx`。
4. 补齐 reduced motion 规则。

### 验收

1. 首页以外页面也具备同一品牌壳层感。
2. 不再出现页面级硬编码主背景色。

## Wave 2：Landing 改造

### 目标

让首页成为编辑杂志风统一系统的示范页。

### 任务

1. Hero 改造
2. Section 编排改造
3. CTA 区改造
4. landing 子组件风格统一

### 验收

1. Landing 与内部主题一眼同源。
2. 主品牌色与内部一致。

## Wave 3：Chat 与 Search 壳层统一

### 目标

统一工作台主链路。

### 任务

1. ChatHeader / SessionSidebar / ComposerInput 改造
2. SearchSidebar / SearchToolbar / SearchResultsPanel 改造
3. 统一侧栏标题、分组标题、边线和卡片系统

### 验收

1. Chat 与 Search 在视觉上像同一工作台的两个模式。
2. 主列、边注列、目录列关系一致。

## Wave 4：KB 与长尾页面统一

### 目标

把 KB、Settings、Auth、Notes、Read 补齐到同一系统。

### 任务

1. KB 列表页重组
2. Settings / Auth 统一
3. Read / Notes 统一

### 验收

1. 任意页面切换都不再出现品牌断层。

## Wave 5：细节 polish 与可访问性收口

### 目标

收尾并建立长期维护基线。

### 任务

1. 减少小字号大写标签滥用
2. 统一 focus-visible
3. 统一 hover 和 active
4. 补 ARIA 标签缺口
5. reduced motion 测试

## 9. 文件级执行清单

### 第一批必须修改

- `apps/web/src/styles/theme.css`
- `apps/web/src/styles/global.css`
- `apps/web/src/app/components/Layout.tsx`
- `apps/web/src/app/components/landing/Logo.tsx`
- `apps/web/src/app/pages/Landing.tsx`
- `apps/web/src/features/chat/components/ChatHeader.tsx`
- `apps/web/src/features/chat/components/session-sidebar/SessionSidebar.tsx`
- `apps/web/src/features/chat/components/composer-input/ComposerInput.tsx`
- `apps/web/src/features/search/components/SearchWorkspace.tsx`
- `apps/web/src/features/search/components/SearchSidebar.tsx`
- `apps/web/src/app/pages/KnowledgeBaseList.tsx`

### 第二批高优先级跟进

- `apps/web/src/app/components/SearchResultCard.tsx`
- `apps/web/src/app/components/KnowledgeBaseCard.tsx`
- `apps/web/src/app/components/EmptyState.tsx`
- `apps/web/src/features/chat/components/ChatRightPanel.tsx`
- `apps/web/src/features/chat/components/message-feed/*`
- `apps/web/src/features/chat/components/workbench/*`
- `apps/web/src/app/pages/Settings.tsx`
- `apps/web/src/app/pages/Login.tsx`
- `apps/web/src/app/pages/Register.tsx`
- `apps/web/src/app/pages/ForgotPassword.tsx`
- `apps/web/src/app/pages/ResetPassword.tsx`

### 第三批统一补齐

- `apps/web/src/app/pages/Read.tsx`
- `apps/web/src/app/pages/Notes.tsx`
- `apps/web/src/features/kb/components/*`
- `apps/web/src/app/components/tools/*`

## 10. 非目标

本计划不包含以下事项：

1. 后端接口改造
2. 组件库全面迁移
3. 完整设计稿工具链建设
4. 新增第二套主题模式
5. 为了“杂志感”而重写业务交互逻辑

## 11. 风险与回滚策略

## 11.1 风险

1. 只改首页不改内页，会进一步加剧割裂。
2. 只改颜色不改编排，会得到“暖色 dashboard”，而非 editorial。
3. 过度使用 serif，会损伤工作台正文可读性。
4. 动效过多，会削弱专业感与稳定感。
5. 若不先收 token，后续页面会继续局部返工。

## 11.2 回滚策略

1. 所有页面层改造都应建立在 token 收口之后。
2. 若单页改造效果不稳定，可保留 token 与骨架层改动，回滚具体页面布局。
3. Chat 和 Search 的壳层改造应可分开回滚，不互相阻塞。

## 12. 验收标准

### 12.1 视觉验收

1. 首页与内部页主品牌色一致。
2. serif 只出现在正确层级，正文阅读不受损。
3. 卡片、面板、边线、阴影形成稳定家族特征。
4. 不再出现明显的 startup 冷色科技页与暖纸工作台并存。

### 12.2 交互验收

1. 所有关键交互控件 hover、focus、active 风格一致。
2. 动效克制且支持 reduced motion。
3. 侧栏、主列、边注列在 Chat / Search / KB 三类页面里具备一致语法。

### 12.3 工程验收

1. `apps/web/src/styles/theme.css` 成为主视觉 token 真源。
2. 页面中的硬编码主色显著下降。
3. 新增样式优先走 token，不再引入新品牌色。

### 12.4 用户感知验收

1. 用户进入首页和内页时，会明确感知是同一个产品。
2. 用户能说出 ScholarAI 的视觉记忆点是“研究刊物式工作台”，而不是“普通 AI 对话页”。

## 13. 最终建议执行顺序

推荐严格按以下顺序推进，不建议跳步：

1. 先做 token 与 Layout。
2. 再做 Landing。
3. 再做 Chat 与 Search。
4. 再做 Knowledge Base。
5. 最后补 Settings、Auth、Read、Notes。

原因很简单：

- 不先收口 token，后面所有页面都会反复返工。
- Landing 不先对齐，品牌就无法统一。
- Chat 与 Search 是内部工作台感知最强的两页，必须尽早统一。
- KB 和长尾页面适合作为系统化收尾，而不是起点。

## 14. 最小验证命令

按仓库规则，前端改动至少执行：

```bash
cd apps/web && npm run type-check
```

若涉及结构/治理类文档联动，再补充：

```bash
bash scripts/check-runtime-hygiene.sh tracked
bash scripts/check-doc-governance.sh
bash scripts/check-structure-boundaries.sh
bash scripts/check-code-boundaries.sh
bash scripts/check-governance.sh
```
