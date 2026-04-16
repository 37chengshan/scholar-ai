# ScholarAI 结构问题整改计划 v1

## 1. 文档目的

这份文档不是原则说明，而是面向当前仓库的**可执行整改方案**。目标有三个：

1. 把当前"治理骨架已搭出，但真实代码主路径与分层尚未完全收口"的状态，推进到**单一真源**状态。
2. 把前端、后端、接口契约、治理脚本、文档系统统一到一套能持续演进的工程基线上。
3. 给出**明确的实践顺序、要改哪些目录、要改哪些文件、每一步如何验收**。

本计划基于当前仓库实际结构制定，已核对到以下现状：

- 根目录已有 `apps/`、`packages/`、`docs/`、`infra/`、`scripts/`、`frontend/`、`backend-python/`
- `apps/web` 与 `apps/api` 当前仍是**逻辑映射层**，真实代码仍在 `frontend/` 与 `backend-python/`
- `docs/architecture`、`docs/development`、`docs/governance` 已建立治理主干
- `scripts/check-doc-governance.sh` 与 `scripts/check-code-boundaries.sh` 当前可通过
- `scripts/check-structure-boundaries.sh` 当前失败，原因是仓库缺少 `.github/workflows`
- 前端仍存在重复 hook：`frontend/src/hooks/useKnowledgeBases.ts` 与 `frontend/src/app/hooks/useKnowledgeBases.ts`
- 后端 `backend-python/app/api/search.py` 与 `backend-python/app/api/search/` 并存
- 后端 `backend-python/app/models/` 中混放 ORM 模型与 Pydantic schema
- 后端 `backend-python/app/api/papers/paper_crud.py` 仍直接做 SQL 查询、过滤、分页和响应拼装
- API 契约文档与真实实现存在漂移，例如分页文档写 `limit/offset + meta.total`，而 `papers` 真实接口使用 `page/limit + totalPages`；字段命名文档要求"边界一次转换"，而 `paper_shared.py` 的响应同时混用 `snake_case` 与 `camelCase`

---

## 2. 当前问题定性

当前仓库不是"没有结构"，而是处于**半治理、半迁移、半收口**状态。这个阶段最危险的不是代码脏，而是：

- 新目录开始出现，但旧目录仍在继续承接变更
- 文档开始成为真源，但代码尚未完全服从文档
- 边界脚本开始工作，但门禁本身还未闭环
- 前后端都有分层目录，但职责边界尚未锁死

如果不继续推进收口，后果会是：

1. **双主路径固化**：`apps/*` 和 `frontend/backend-python` 长期并存，未来再迁移成本更高。
2. **前端局部重复实现继续增长**：同一领域逻辑可能继续在 `app/hooks` 和 `hooks` 两边生长。
3. **后端 service 无法成为唯一业务入口**：router 继续膨胀，后续测试和拆分困难。
4. **API 契约持续漂移**：前端 service 层被迫长期做兼容补丁。
5. **治理文档失去约束力**：文档写的是目标，代码跑的是另一套现实。

---

## 3. 本次整改的最佳实践方案

### 3.1 选定的总体策略

**最佳方案不是现在立刻做物理迁移，也不是继续保持映射层长期存在。**

当前最优实践是：

> **先在现有真实代码路径 (`frontend/`、`backend-python/`) 上完成分层收口与契约收口，再把 `apps/*` 从"逻辑映射层"升级为真正的物理主路径。**

原因：

- 当前 `apps/web`、`apps/api` 只是占位目录，没有真实业务代码。
- 若现在直接把全部代码物理搬到 `apps/*`，会把"仓库迁移"与"代码分层整改"叠加，风险过高。
- 当前最大问题不是路径名字，而是**同一职责多处落地、router 过厚、schema 与 ORM 混放、契约漂移**。
- 先在现有路径完成治理，再迁移，会让迁移只是"搬运"，不是"重构 + 搬运 + 修 bug"三件事同时做。

### 3.2 本期不做的事

本计划明确不做：

- 不在本轮内把全部前端代码直接搬到 `apps/web`
- 不在本轮内把全部后端代码直接搬到 `apps/api`
- 不在本轮内一次性把 `core/` 全部拆完
- 不在本轮内引入新的架构层级（例如立刻做完整 DDD）
- 不在本轮内让 `packages/ui`、`packages/types`、`packages/sdk` 承接大规模真实代码

### 3.3 本期必须做到的结果

本轮整改结束后，必须达到以下状态：

1. **治理门禁闭环**：四个治理脚本全部通过。
2. **单一真源**：明确 `frontend/` 与 `backend-python/` 是当前唯一代码主路径，`apps/*` 仍只作映射入口且禁止写业务代码。
3. **前端消除重复实现入口**：同一业务 hook 不再双份存在。
4. **后端 service 成为业务真源**：router 逐步只保留协议处理。
5. **后端 schema 与 ORM 分离**：新增 `app/schemas/`。
6. **API 契约收口**：分页、响应壳、字段命名有一套明确标准，真实代码开始按该标准收敛。

---

## 4. 当前仓库的关键结构问题与证据

## 4.1 仓库层问题

### 问题 A：`apps/*` 已被定义为长期边界，但还不是实际主路径

现状：
- `apps/web` 只有 README
- `apps/api` 只有 README
- 真正代码在 `frontend/` 和 `backend-python/`

影响：
- 新成员或 AI 容易误以为 `apps/*` 是真实实现目录
- 未来若有人开始往 `apps/*` 写新代码，会立刻形成双主路径

整改原则：
- 本轮不迁移真实代码
- 但必须把 `apps/*` 的"映射层身份"写死，并通过文档和校验保证不承接业务代码

### 问题 B：门禁要求 `.github/workflows`，仓库当前不存在

现状：
- `scripts/check-structure-boundaries.sh` 把 `.github/workflows` 作为 required directory
- 当前仓库无 `.github/`
- 该脚本当前失败

影响：
- 治理门禁无法闭环
- 文档写了 PR 流程与治理脚本，但缺少真正的 CI 容器入口

整改原则：
- 本轮必须补 `.github/workflows`
- 至少提供一条最小治理流水线，运行四个治理脚本和前后端最小校验命令

---

## 4.2 前端层问题

### 问题 C：同一领域 hook 双份存在

现状：
- `frontend/src/hooks/useKnowledgeBases.ts`
- `frontend/src/app/hooks/useKnowledgeBases.ts`

而且两份实现契约不同：
- root 版本返回 `createKB/deleteKB -> boolean`
- `app/hooks` 版本返回 `createKB -> KnowledgeBase`、`deleteKB -> void`，并带 `total`

影响：
- 页面调用方无法形成稳定预期
- 业务逻辑继续分裂
- AI 修改时容易改到错误版本

整改原则：
- 同一业务 hook 只能保留一份 canonical implementation
- 另一份必须删除或改成薄包装兼容层，并附下线计划

### 问题 D：前端分层仍然带有"历史层 + 新层"并存

现状：
- `frontend/src/app/` 已承接页面、局部 hooks、局部 contexts 和大量 components
- 同时根级仍有 `hooks/`、`contexts/`、`services/`、`stores/`
- `app/components` 已分类为 `ui/`、`landing/`、`tools/`、`papers/`、`notes/`，但业务功能仍集中堆放在同一大目录

影响：
- `app` 的边界不够明确
- 组件目录容易继续膨胀
- feature 层没有真正浮出水面

整改原则：
- 本轮不强推全面 `features/*` 化
- 先把 `app` 定位锁死为"路由/页面装配/页面局部逻辑"
- 根级 `services/hooks/stores/types/utils` 作为共享层
- 后续再渐进式把业务组件从 `app/components` 抽到 `features/*`

### 问题 E：service 返回契约不一致

现状：
- `papersApi.ts` 中有的方法返回裸实体，有的方法返回 `{ success, data }` 包装后的对象
- `kbApi.ts` 大量方法又统一手工包一层 `ApiResponse`
- 前端 `apiClient` 已在拦截器层做统一解包，但 service 层并未完全统一消费方式

影响：
- 页面 / hook 必须记忆"哪个 service 返回什么"
- 契约不透明
- 测试和类型约束难统一

整改原则：
- service 层统一只返回**业务 DTO**，不再由每个 service 自行决定是否包 `{ success, data }`
- 若保留 `ApiResponse<T>`，只能出现在 apiClient 边界或 SDK 层，不进入页面消费层

---

## 4.3 后端层问题

### 问题 F：router 仍直接承担业务与数据访问

现状：
- `backend-python/app/api/papers/paper_crud.py` 中直接做：
  - 分页参数修正
  - SQLAlchemy 查询构造
  - `ReadingProgress` 关联筛选
  - 总数统计
  - 响应格式拼装

影响：
- API 层无法保持轻薄
- service 层无法成为唯一业务真源
- 同类逻辑难复用、难测试

整改原则：
- API 层只做：收参、鉴权、调用 service、返回 schema
- 查询和业务筛选下沉到 `services/` + `repositories/`

### 问题 G：`models/` 中混放 ORM 模型与 Pydantic schema

现状：
- `backend-python/app/models/note.py` 是 Pydantic 请求/响应模型
- `backend-python/app/models/orm_note.py` 是 SQLAlchemy ORM 模型

影响：
- `models` 语义混乱
- 导入路径难读
- 新人和 AI 难以判断"模型"到底是数据库模型还是接口模型

整改原则：
- 本轮新增 `backend-python/app/schemas/`
- `models/` 仅保留 ORM / persistence 模型
- `schemas/` 统一承接请求/响应模型

### 问题 H：同名模块与目录并存

现状：
- `backend-python/app/api/search.py`
- `backend-python/app/api/search/`

影响：
- search 领域边界不清晰
- 路由入口容易重复或绕路
- 未来拆分 search 相关能力时认知成本高

整改原则：
- 只保留一种 canonical 结构
- 结合当前已有 grouped API 方向，最佳实践是保留 `app/api/search/` 目录，逐步吸收 `search.py` 的内容，最后删除 `search.py`

### 问题 I：`core/` 偏胖

现状：
- `backend-python/app/core/` 下约 64 个 Python 文件
- 同时混有：配置、数据库、agent、embedding、reranker、docling、图谱、意图识别等

影响：
- `core` 失去语义，成为总收纳箱
- 后续依赖方向失控
- 很难建立"基础设施层"和"能力层"的边界

整改原则：
- 本轮不一次性拆空 `core`
- 先冻结其职责：`core` 只允许新增基础设施能力，不允许再塞业务/检索/模型编排新代码
- 仅对本轮要动的模块做最小迁移，后续分波次迁出

---

## 4.4 契约层问题

### 问题 J：文档契约与真实实现不一致

#### 例 1：分页协议漂移

文档：
- `docs/architecture/api-contract.md` 定义分页为 `limit + offset`，响应在 `meta.limit/meta.offset/meta.total`

真实实现（papers）：
- 请求用 `page + limit`
- 返回 `data.total/page/limit/totalPages`

#### 例 2：命名风格漂移

文档：
- 约定"命名风格转换只在 API 边界进行一次"

真实实现：
- `backend-python/app/api/papers/paper_shared.py` 返回对象内同时存在：
  - `arxiv_id`
  - `file_size`
  - `created_at`
  - `processingStatus`
  - `processingError`

这意味着同一个 payload 里混用 `snake_case` 与 `camelCase`。

#### 例 3：前端被迫兼容历史差异

`frontend/src/services/papersApi.ts` 中 `normalizePaper()` 同时兼容：
- `arxivId` / `arxiv_id`
- `storageKey` / `storage_key`
- `fileSize` / `file_size`
- `readingNotes` / `reading_notes`

影响：
- 契约不再是单一真源
- service 层变成长期补丁层

整改原则：
- 本轮必须选定一套**前端消费协议**作为 canonical contract
- 最佳实践：**前端只消费 camelCase DTO，后端在 API 边界输出一次性 camelCase**
- 后端内部数据库、ORM、service、repository 继续保持 snake_case

---

## 5. 本次整改的目标状态

## 5.1 仓库目标状态

### 当前阶段（本轮整改结束时）

- `frontend/`：唯一前端真实代码主路径
- `backend-python/`：唯一后端真实代码主路径
- `apps/web`、`apps/api`：仅保留 README 和映射说明，不承接业务代码
- `.github/workflows/`：存在，并运行治理脚本
- `docs/`：继续作为唯一文档系统
- `packages/`：仅作为未来公共资产容器，不承接核心业务实现

### 下一阶段（后续里程碑）

- 当前路径收口完成后，再做物理迁移到 `apps/*`
- `packages/types`、`packages/sdk` 再开始承接真实共享契约

## 5.2 前端目标状态

- `frontend/src/app` 只保留：
  - `App.tsx`
  - `routes.tsx`
  - `pages/`
  - 页面专属 hooks / contexts / 组件
- `frontend/src/services`：唯一 HTTP / SSE 访问层
- `frontend/src/hooks`：共享业务 hook
- `frontend/src/stores`：全局状态
- `frontend/src/types`：前端 DTO / 视图模型
- 同一业务 hook 只保留一份实现

## 5.3 后端目标状态

- `backend-python/app/api`：只保留协议入口
- `backend-python/app/services`：业务编排真源
- `backend-python/app/repositories`：数据访问层（本轮新增）
- `backend-python/app/models`：ORM 模型
- `backend-python/app/schemas`：请求/响应模型（本轮新增）
- `backend-python/app/core`：仅基础设施

## 5.4 契约目标状态

- 前端只消费 camelCase
- 后端对外 HTTP 响应统一为 camelCase
- 列表接口统一响应壳
- 分页策略统一，不允许同一资源内一部分用 `page`，另一部分用 `offset`

---

## 6. 分阶段整改实施方案

# Phase 0：治理门禁闭环（优先级 P0，预计 0.5~1 天）

## 目标

让仓库治理脚本四项全部通过；把"规则写了但门禁不完整"的状态先补齐。

## 要做的事

### 任务 0.1：新增 `.github/workflows/`

新增目录：
- `.github/workflows/`

新增文件：
- `.github/workflows/governance.yml`

最小工作流内容建议：
- checkout
- setup node
- setup python
- 执行：
  - `bash scripts/check-doc-governance.sh`
  - `bash scripts/check-structure-boundaries.sh`
  - `bash scripts/check-code-boundaries.sh`
  - `bash scripts/check-governance.sh`

### 任务 0.2：新增 `.github/PULL_REQUEST_TEMPLATE.md`

当前文档已经引用 PR 流程，但仓库缺少实际模板承接。新增：
- `.github/PULL_REQUEST_TEMPLATE.md`

模板字段至少包含：
- Summary
- Background
- Changes
- Contract impact
- Verification
- Risks
- Docs updated

### 任务 0.3：给 `apps/web`、`apps/api` 的 README 加"禁止承接业务代码"说明

修改：
- `apps/web/README.md`
- `apps/api/README.md`

新增说明：
- 当前阶段只做逻辑映射
- 不允许新业务代码直接落入 `apps/*`
- 真实代码主路径仍是 `frontend/`、`backend-python/`

## 验收标准

执行：

```bash
bash scripts/check-doc-governance.sh
bash scripts/check-structure-boundaries.sh
bash scripts/check-code-boundaries.sh
bash scripts/check-governance.sh
```

必须全部通过。

---

# Phase 1：主路径冻结与仓库真源收口（优先级 P0，预计 1 天）

## 目标

明确"当前真正的代码主路径"，禁止结构继续扩散。

## 要做的事

### 任务 1.1：更新 `README.md`

在 `Rules` 或 `Scope` 中明确补充：

- `frontend/` 是当前唯一前端真实代码主路径
- `backend-python/` 是当前唯一后端真实代码主路径
- `apps/*` 仅作逻辑映射与未来迁移占位
- 未经架构变更批准，不得在 `apps/*` 中新增业务实现

### 任务 1.2：更新 `AGENTS.md`

新增硬规则：
- AI 修改前端代码时，只允许进入 `frontend/`
- AI 修改后端代码时，只允许进入 `backend-python/`
- 若变更落到 `apps/*`，必须被视为结构违规

### 任务 1.3：加强结构边界脚本

修改 `scripts/check-structure-boundaries.sh`：
- 新增检查：`apps/web` 与 `apps/api` 中若出现 `.ts/.tsx/.js/.py` 真实业务代码，则失败
- 允许存在 README 和占位文档

建议检测逻辑：
- `find apps/web -type f \( -name '*.ts' -o -name '*.tsx' -o -name '*.js' -o -name '*.jsx' \)`
- `find apps/api -type f \( -name '*.py' -o -name '*.ts' -o -name '*.js' \)`
- 若结果不为空且不在白名单（README）中，直接 fail

## 验收标准

- `README.md`、`AGENTS.md`、`apps/*/README.md` 一致表达当前主路径
- `scripts/check-structure-boundaries.sh` 能阻止 `apps/*` 承接真实业务代码

---

# Phase 2：前端分层收口（优先级 P0/P1，预计 2~4 天）

## 目标

把前端从"历史层 + 新层并存"收敛到一套清晰边界。

## 本轮选定的前端最佳实践

当前最优做法不是立即全面 `features/*` 化，而是先把边界锁死：

- `src/app`：应用壳、路由、页面、页面专属局部逻辑
- `src/services`：唯一 API/SSE 访问层
- `src/hooks`：共享业务 hook
- `src/stores`：全局状态
- `src/types`：共享类型
- `src/lib` / `src/utils`：基础工具

### 为什么这比立刻 `features/*` 化更好

因为你当前问题首先是**重复实现与入口分散**，不是 feature 目录名字不够漂亮。先收口，再按业务领域抽 feature，风险更低。

## 要做的事

### 任务 2.1：消除重复 hook `useKnowledgeBases`

保留建议：
- **保留 `frontend/src/hooks/useKnowledgeBases.ts` 作为共享 canonical hook**
- 删除 `frontend/src/app/hooks/useKnowledgeBases.ts`

原因：
- Knowledge base 列表不是单一页面的专属逻辑，而是明显的共享业务 hook
- 放在根级 `hooks/` 更符合当前边界设计

具体改法：
1. 统一定义 `UseKnowledgeBasesResult` 契约，建议保留更完整版本：
   - `knowledgeBases`
   - `total`
   - `loading`
   - `error`
   - `refetch`
   - `createKB`
   - `deleteKB`
2. 把 `app/hooks/useKnowledgeBases.ts` 中更完整的行为合并到 root 版本
3. 全局搜索并修改 import：
   - 从 `@/app/hooks/useKnowledgeBases` 改到 `@/hooks/useKnowledgeBases`
4. 删除 `frontend/src/app/hooks/useKnowledgeBases.ts`
5. 给 `scripts/check-code-boundaries.sh` 或新增脚本补一个简单检查：禁止 `app/hooks` 与 `hooks` 出现同名文件

### 任务 2.2：明确 `app/hooks` 的允许范围

保留在 `frontend/src/app/hooks/` 的仅限：
- 强依赖路由/页面生命周期/页面局部 UI 流程的 hook

当前可以保留的类别：
- `useChatStream.ts`
- `useSessions.ts`
- `useUpload.ts`
- `useDashboard.ts`
- `useAutoSave.ts`
- `useSSE.ts`

禁止新增：
- 与资源域通用列表、CRUD 查询相关的共享 hook

把这条规则写入：
- `docs/development/coding-standards.md`
- `AGENTS.md`

### 任务 2.3：统一 service 返回值规范

选定规则：

> `frontend/src/services/*` 一律返回业务 DTO，不返回二次包装的 `{ success, data }` 给页面层。

具体执行：

1. 保留 `apiClient` 负责底层统一请求/错误处理
2. `services/*` 统一返回：
   - 实体对象
   - 列表对象
   - 状态对象
3. 如果需要 `ApiResponse<T>`，限定只允许出现在：
   - `apiClient.ts`
   - 未来 `packages/sdk`
4. 逐步调整：
   - `kbApi.ts`
   - `papersApi.ts`
   - `chatApi.ts`
   - `uploadApi.ts`

#### 具体示例：`kbApi.ts`

当前：
```ts
return { success: true, data: response.data }
```

整改后建议：
```ts
return response.data as KnowledgeBaseListDto
```

然后 `useKnowledgeBases` 只处理 DTO，不再判断 `response.success && response.data`。

### 任务 2.4：冻结 `app/components` 的职责

当前 `app/components` 已经较大。本轮不大搬家，但先定规则：

- `app/components/ui/`：允许存在通用 UI
- `app/components/landing/`：允许存在 landing 专属组件
- `app/components/tools/`：允许存在工具型复合组件
- `app/components/papers/`、`notes/`：继续保留，但**禁止继续扩张**

新增业务组件的落点原则：
- 若是页面专属复合组件，可先放 `app/pages/<page>/components`（本轮新建）
- 若是跨页面业务组件，优先建立：
  - `src/features/papers/components`
  - `src/features/notes/components`
  - `src/features/chat/components`

本轮只要求建立目录和准入规则，不要求一次性搬迁全部组件。

### 任务 2.5：状态层规则落地

更新 `docs/development/coding-standards.md`：

- React Query：服务端数据缓存
- store：跨页面全局状态（用户、UI、当前会话上下文）
- context：主题/语言/认证外壳等少量跨树注入
- hooks：封装交互流程，不做持久全局状态真源

## 验收标准

- `useKnowledgeBases` 只保留一份实现
- 页面与 `app/components` 不直接请求 API
- 至少一类 service（建议 `kbApi`）完成 DTO 化
- 文档补齐前端边界规则
- `npm run type-check` 通过
- `npm run test:run` 冒烟通过

---

# Phase 3：后端分层整改（优先级 P0/P1，预计 4~7 天）

## 目标

把"router 仍做太多事"的状态，推进到"service 是唯一业务编排真源"。

## 本轮选定的后端最佳实践

当前最优路径不是直接大拆 DDD，而是采用**标准三段式**：

- `api/`：协议入口
- `services/`：业务编排
- `repositories/`：数据库访问

并在此基础上把 `schemas/` 从 `models/` 中拆出。

## 要做的事

### 任务 3.1：新增 `backend-python/app/schemas/`

新增目录：
- `backend-python/app/schemas/`

首批迁移文件建议：
- `backend-python/app/models/note.py` -> `backend-python/app/schemas/note.py`
- `backend-python/app/models/session.py` -> `backend-python/app/schemas/session.py`
- `backend-python/app/models/rag.py` -> `backend-python/app/schemas/rag.py`
- `backend-python/app/models/reading_progress.py` -> `backend-python/app/schemas/reading_progress.py`
- `backend-python/app/api/papers/paper_shared.py` 中的 request/response model -> 拆成 `backend-python/app/schemas/papers.py`

### 任务 3.2：收紧 `models/`

整改后规则：
- `models/` 只允许 SQLAlchemy ORM 或数据库持久化模型
- 禁止新增 Pydantic `BaseModel` 到 `models/`

需要同步更新：
- `docs/development/coding-standards.md`
- `AGENTS.md`
- `docs/governance/code-boundary-baseline.md`

### 任务 3.3：新增 `backend-python/app/repositories/`

新增目录：
- `backend-python/app/repositories/`

第一批 repository 建议：
- `paper_repository.py`
- `knowledge_base_repository.py`
- `import_job_repository.py`
- `reading_progress_repository.py`

其中 `paper_repository.py` 至少承接：
- list 查询
- search 查询
- count 查询
- status 相关查询

### 任务 3.4：拆 `paper_crud.py`

这是后端分层整改第一批样板工程，必须优先做。

#### 当前问题
`paper_crud.py` 直接做了：
- 分页参数归一化
- ORM 查询拼装
- 业务筛选（starred、readStatus、date range）
- count
- DTO 格式化

#### 整改后的目标结构

- `app/api/papers/paper_crud.py`
  - 只保留 FastAPI endpoint 和依赖注入
- `app/services/paper_service.py`
  - 提供 `list_papers(...)`、`search_papers(...)`
- `app/repositories/paper_repository.py`
  - 提供真正的 SQLAlchemy 查询
- `app/schemas/papers.py`
  - `PaperListQuery`、`PaperListItem`、`PaperListResponse`

#### 具体改法

1. 新增 `PaperListQuery` schema：
   - `page` 或 `offset`（见 Phase 4 契约统一）
   - `limit`
   - `starred`
   - `read_status`
   - `date_from`
   - `date_to`
2. 在 router 中只解析参数并传给 service
3. 在 service 中调用 repository 查询数据
4. `format_paper_response` 迁出 `paper_shared.py`，转移到 schema conversion 层或 service 内私有 mapper
5. 删除 router 内直接 `db.execute` / `select` / `func.count`

### 任务 3.5：收口 `api/search.py` 与 `api/search/`

最佳做法：
- 保留 `backend-python/app/api/search/` 目录作为 canonical search API area
- 将 `search.py` 中仍有效的入口迁入：
  - `search/library.py`
  - `search/external.py`
  - `search/multimodal.py`
  - `search/shared.py`
- 更新主路由注册
- 删除 `search.py`

执行步骤：
1. 先确认 `main.py` 或 API 注册文件对 `search.py` 的引用位置
2. 把引用改到 package router
3. 跑搜索相关接口 smoke test
4. 删除 `search.py`

### 任务 3.6：冻结 `core/` 的新增准入

本轮不做全面迁移，但必须立规则：

新增到 `core/` 的文件只能属于：
- config
- database
- logging
- security
- base exceptions
- infra clients

不允许再新增到 `core/` 的文件类型：
- 资源域业务逻辑
- 路由相关封装
- 面向具体用户能力的 orchestrator
- 新的检索业务组合逻辑

需要新增文档：
- `docs/governance/core-boundary-baseline.md`（建议）

### 任务 3.7：收紧 code boundary baseline

当前 `docs/governance/code-boundary-baseline.md` 允许多份 API 文件继续直连数据库。这是现实，但必须分波次削减。

本轮目标：
- 至少完成 `paper_crud.py` 从 allowlist 中移除
- 若进度允许，再处理：
  - `paper_status.py`
  - `kb/kb_crud.py`

## 验收标准

- `app/schemas/` 建立并承接首批 schema
- `models/` 不再新增 Pydantic 模型
- `paper_crud.py` 不再直接访问数据库
- `api/search.py` 被删除或明确标记 deprecated 且不再承接新路由
- `code-boundary-baseline` allowlist 至少减少 1 项
- 后端单测/冒烟通过

---

# Phase 4：API 契约统一（优先级 P0，预计 2~3 天）

## 目标

把"文档里一套、实现里一套、前端兼容一套"的状态，统一成一套明确可执行的 API 契约。

## 本轮选定的最佳实践

### 契约决策 1：前端消费协议统一 camelCase

- 前端页面、hooks、store、types 全部只消费 camelCase
- 后端内部仍用 snake_case
- 命名转换只发生在 API 边界一次

### 契约决策 2：统一列表响应壳

当前文档采用：
```json
{
  "success": true,
  "data": [],
  "meta": {"limit": 20, "offset": 0, "total": 100}
}
```

当前 papers 实现采用：
```json
{
  "success": true,
  "data": {
    "papers": [...],
    "total": 100,
    "page": 1,
    "limit": 20,
    "totalPages": 5
  }
}
```

两者必须统一。

### 推荐最终方案

对列表接口统一为：
```json
{
  "success": true,
  "data": {
    "items": [...]
  },
  "meta": {
    "limit": 20,
    "offset": 0,
    "total": 100
  }
}
```

原因：
- 和文档当前方向一致
- 对前端更通用，不绑死具体资源名 `papers`
- 为未来 SDK 和共享类型铺路

### 契约决策 3：分页统一到 `limit + offset`

因为当前 `docs/architecture/api-contract.md` 已经写了 `limit/offset`。最佳实践是：
- 不改文档去追随旧实现
- 改旧实现去服从文档

过渡方式：
- 在一个版本周期内，后端暂时兼容 `page + limit`
- 但 service/schema 统一使用 `limit + offset`
- 前端新代码全部改为 `limit + offset`
- 兼容结束后删除 `page`

## 要做的事

### 任务 4.1：更新 `docs/architecture/api-contract.md`

补充明确条目：
- 列表接口统一 `data.items + meta`
- 前端 DTO 一律 camelCase
- 后端 API 输出为 camelCase
- 旧接口兼容策略与退场时限

### 任务 4.2：新增 `backend-python/app/schemas/common.py`

定义通用响应壳：
- `SuccessResponse[T]`
- `ListMeta`
- `ListResponse[T]`
- `ProblemDetailResponse`

### 任务 4.3：首批落地到 `papers`

修改：
- `backend-python/app/api/papers/paper_shared.py` 或迁移后 `schemas/papers.py`
- `frontend/src/services/papersApi.ts`
- `frontend/src/types/*`

目标：
- 后端输出 camelCase paper DTO
- 列表返回 `items + meta`
- 前端移除一部分 normalize 兼容逻辑

### 任务 4.4：收敛 `kbApi` 和 `papersApi`

使两个 service 都遵循相同模式：
- 不再手工包 `{ success, data }`
- 都消费统一 DTO

## 验收标准

- 文档与真实实现一致
- `papers` 列表接口完成新协议落地
- `papersApi.ts` 兼容代码明显减少
- 后端 payload 不再混用 snake_case + camelCase

---

# Phase 5：为后续物理迁移与 packages 承接做准备（优先级 P2，预计 1~2 天）

## 目标

让下一阶段的物理迁移变成机械操作，而不是再次架构重构。

## 要做的事

### 任务 5.1：补 `packages` 真实承接策略

当前 `packages/config`、`packages/sdk`、`packages/types`、`packages/ui` 只有 README。此阶段不承接业务代码，但要明确未来拆分标准：

- `packages/types`：只放跨前后端共享 DTO 类型，前提是 API 契约稳定
- `packages/sdk`：只放经过契约统一后的前端 API client 封装
- `packages/ui`：只放真正跨页面、跨产品域的 UI primitive
- `packages/config`：只放 lint/tsconfig/构建共享配置

### 任务 5.2：建立迁移条件清单

只有同时满足以下条件，才允许物理迁移到 `apps/*`：

1. 前端无重复 hook / 重复服务入口
2. 后端已有 `schemas/` 和 `repositories/`
3. `search.py` 单文件入口已下线
4. `papers` 契约已统一到 `items + meta` / camelCase
5. `apps/*` 没有新增业务代码
6. CI 工作流已稳定通过

### 任务 5.3：新增 ADR

建议新增：
- `docs/adr/0002-delay-physical-migration-until-boundary-convergence.md`

记录本次决策：
- 为什么暂缓物理迁移
- 为什么先做边界收口和契约统一

## 验收标准

- `packages/*` 的承接边界清楚
- 迁移条件列出并写入文档
- ADR 存档

---

## 7. 具体文件修改清单

以下是建议直接落地的文件清单。

## 7.1 新增文件

### 仓库治理
- `.github/workflows/governance.yml`
- `.github/PULL_REQUEST_TEMPLATE.md`
- `docs/adr/0002-delay-physical-migration-until-boundary-convergence.md`
- `docs/governance/core-boundary-baseline.md`（建议）

### 后端分层
- `backend-python/app/schemas/__init__.py`
- `backend-python/app/schemas/common.py`
- `backend-python/app/schemas/note.py`
- `backend-python/app/schemas/session.py`
- `backend-python/app/schemas/papers.py`
- `backend-python/app/repositories/__init__.py`
- `backend-python/app/repositories/paper_repository.py`
- `backend-python/app/repositories/reading_progress_repository.py`

### 前端分层（可选但推荐）
- `frontend/src/features/README.md`
- `frontend/src/features/papers/.gitkeep`
- `frontend/src/features/notes/.gitkeep`
- `frontend/src/features/chat/.gitkeep`

## 7.2 必改文件

### 仓库与文档
- `README.md`
- `AGENTS.md`
- `apps/web/README.md`
- `apps/api/README.md`
- `docs/architecture/api-contract.md`
- `docs/development/coding-standards.md`
- `docs/governance/code-boundary-baseline.md`
- `scripts/check-structure-boundaries.sh`
- `scripts/check-code-boundaries.sh`（如增加同名 hook 检查）

### 前端
- `frontend/src/hooks/useKnowledgeBases.ts`
- `frontend/src/app/hooks/useKnowledgeBases.ts`（删除）
- `frontend/src/services/kbApi.ts`
- `frontend/src/services/papersApi.ts`
- 相关页面 import 路径

### 后端
- `backend-python/app/api/papers/paper_crud.py`
- `backend-python/app/api/papers/paper_shared.py`
- `backend-python/app/services/paper_service.py`
- `backend-python/app/api/search.py`（删除或迁移后下线）
- `backend-python/app/models/note.py`（迁移后删除）
- `backend-python/app/models/session.py`（迁移后删除）

---

## 8. 推荐执行顺序（严格顺序）

必须按下面顺序执行，不要并行乱改：

1. **补 `.github/workflows` 与 PR 模板**
2. **让四个治理脚本全通过**
3. **冻结主路径：README / AGENTS / apps README / structure script**
4. **前端消灭 `useKnowledgeBases` 双实现**
5. **统一前端 service 返回契约（先从 `kbApi` 或 `papersApi` 选一个做样板）**
6. **后端建立 `schemas/` 与 `repositories/`**
7. **改造 `paper_crud.py` 样板**
8. **收口 `api/search.py` 与 `api/search/`**
9. **统一 `papers` API 契约**
10. **补 ADR 与 packages 承接边界**

不要一开始就：
- 先搬目录
- 先拆 `core`
- 先全量 `features/*`
- 先做 packages 真正承接

那样会同时引爆多个变量。

---

## 9. 最小可交付里程碑（建议拆成 3 个 PR）

## PR-1：治理闭环 PR

范围：
- `.github/workflows`
- PR 模板
- `README.md`
- `AGENTS.md`
- `apps/*/README.md`
- `scripts/check-structure-boundaries.sh`

验收：
- 四个治理脚本全通过

## PR-2：前端收口 PR

范围：
- 删除 `app/hooks/useKnowledgeBases.ts`
- 统一 `useKnowledgeBases` 契约
- service 返回规则样板化
- 文档更新

验收：
- type-check 通过
- 前端测试冒烟通过

## PR-3：后端样板 PR

范围：
- 新增 `schemas/`
- 新增 `repositories/`
- 改造 `paper_crud.py`
- 收口 `search.py`
- 更新 `code-boundary-baseline`

验收：
- pytest 冒烟通过
- baseline allowlist 减少至少 1 项
- papers 契约样板跑通

---

## 10. 风险与回滚策略

## 风险 1：契约统一导致前端页面大面积联调

控制方式：
- 先只在 `papers` 领域做样板
- 前端 service 保留一层临时兼容 adapter
- 页面层不直接承受契约变更

回滚方式：
- 保留旧 DTO adapter 分支
- 若页面联调失败，只回滚 service/schema 映射，不回滚整体目录治理

## 风险 2：后端 router 下沉后测试覆盖不足

控制方式：
- 先做 `paper_crud.py` 一条主链路
- 加 smoke test
- 不一次性改所有 allowlist 文件

回滚方式：
- 保留旧 service path 的小范围切换点
- 单模块回滚，不回滚整个 `schemas/` 目录

## 风险 3：治理文档继续先于代码演进

控制方式：
- 每个整改 PR 都必须附：
  - 受影响文档
  - 运行命令
  - 结构截图或 diff 说明

---

## 11. 完成标准

只有满足下面条件，才算本轮整改完成：

### 仓库治理完成标准
- `.github/workflows` 存在
- 四个治理脚本全部通过
- `apps/*` 不承接业务代码

### 前端完成标准
- 共享业务 hook 无重复实现
- `app` 与根级共享层边界写入规范
- 至少一个 service 域完成 DTO 统一

### 后端完成标准
- `schemas/` 建立
- `repositories/` 建立
- `paper_crud.py` 不再直接访问数据库
- `search.py` 与 `search/` 不再并存为双主入口

### 契约完成标准
- `papers` 领域文档与实现一致
- 前端只消费 camelCase DTO
- 列表接口统一到同一响应壳

---

## 12. 最终结论

这次整改的关键不是再发明更多的目录，而是把当前已经出现的治理框架**落到真实代码边界**上。

当前阶段最优实践可以概括为一句话：

> **先让 `frontend/` 和 `backend-python/` 在现有位置完成单一真源化、分层收口和契约收口；等这些收口完成，再做 `apps/*` 的物理迁移。**

也就是说，当前真正要解决的不是"目录名字不够先进"，而是：

- 同一职责不能多处实现
- router 不能继续承载业务编排
- schema 不能继续和 ORM 混放
- 契约文档不能继续和真实返回不一致
- `apps/*` 不能继续悬空成为未来潜在第二主路径

这份计划按顺序执行后，ScholarAI 会从"治理骨架已搭出但还偏概念化"，进入"仓库、代码、契约、文档、门禁五件事真正对齐"的状态。
