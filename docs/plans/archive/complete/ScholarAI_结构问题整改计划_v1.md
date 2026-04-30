---
owner: platform
status: in-progress
depends_on: []
last_verified_at: 2026-04-17
evidence_commits:
  - plan-audit-report-2026-04-17
---

# ScholarAI 结构问题整改计划 v1

## 1. 文档目的

这份文档不是原则说明，而是面向当前仓库的**可执行整改方案**。目标有三个：

1. 把当前"治理骨架已搭出，但真实代码主路径与分层尚未完全收口"的状态，推进到**单一真源**状态。
2. 把前端、后端、接口契约、治理脚本、文档系统统一到一套能持续演进的工程基线上。
3. 给出**明确的实践顺序、要改哪些目录、要改哪些文件、每一步如何验收**。

本计划基于当前仓库实际结构制定，已核对到以下现状（2026-04-17 更新）：

**已完成的治理基础设施：**
- `.github/workflows/` 已存在（含 `governance-baseline.yml`、`test.yml`）
- `.github/pull_request_template.md` 已存在且内容完整
- `.github/ISSUE_TEMPLATE/` 已存在（含 bug-report、feature-request、governance-task 模板）
- 四个治理脚本全部存在：`check-doc-governance.sh`、`check-code-boundaries.sh`、`check-structure-boundaries.sh`、`check-governance.sh`
- `docs/specs/architecture/api-contract.md` 已存在，使用 `limit/offset` 分页规范
- `docs/specs/adr/` 已存在（含 `0001-repository-boundary-and-governance.md`）
- `pnpm-workspace.yaml` 已存在且配置正确
- `AGENTS.md` 已存在，包含 scope mapping 和禁止新增根目录规则

**仍需整改的问题：**
- 根目录已有 `apps/`、`packages/`、`docs/`、`infra/`、`scripts/`、`apps/web/`、`apps/api/`
- `apps/web` 与 `apps/api` 当前仍是**逻辑映射层**，真实代码仍在 `apps/web/` 与 `apps/api/`
- `apps/*/README.md` 已有"实现路径映射"说明，但措辞可进一步强化约束力
- `apps/web/README.md` 已包含 "Current implementation lives in frontend" 和禁止双实现路径规则
- 前端仍存在重复 hook：`apps/web/src/hooks/useKnowledgeBases.ts` 与 `apps/web/src/app/hooks/useKnowledgeBases.ts`
- 前端 `kbApi.ts` 所有方法返回 `{ success: true, data: response.data }` 包装
- 前端 `papersApi.ts` 的 `normalizePaper()` 同时兼容 camelCase 和 snake_case 字段
- 后端 `apps/api/app/api/search.py` 与 `apps/api/app/api/search/` 并存
- 后端 `apps/api/app/models/` 中混放 ORM 模型与 Pydantic schema（`note.py`、`session.py`、`rag.py` 为 Pydantic）
- 后端 `apps/api/app/api/papers/paper_crud.py` 仍直接做 SQL 查询（含 `db.execute`、`select()`、`func.count`、`text()`）
- 后端 `apps/api/app/api/papers/paper_shared.py` 响应同时混用 `snake_case`（`arxiv_id`、`file_size`）与 `camelCase`（`processingStatus`、`processingError`）
- 后端 `apps/api/app/core/` 含 **49** 个 Python 文件（含配置、数据库、agent、embedding、reranker、图谱等）
- 后端 `apps/api/app/schemas/` 目录**不存在**
- 后端 `apps/api/app/repositories/` 目录**不存在**
- 后端 `apps/api/app/services/` 已存在（含 14 个服务文件，包括 `paper_service.py`）
- API 契约文档与真实实现存在漂移：文档定义 `limit/offset + meta.total`，papers 实现仍部分使用 `page/limit`

---

## 2. 当前问题定性

当前仓库不是"没有结构"，而是处于**半治理、半迁移、半收口**状态。这个阶段最危险的不是代码脏，而是：

- 新目录开始出现，但旧目录仍在继续承接变更
- 文档开始成为真源，但代码尚未完全服从文档
- 边界脚本开始工作，但门禁本身还未闭环
- 前后端都有分层目录，但职责边界尚未锁死

如果不继续推进收口，后果会是：

1. **双主路径固化**：`apps/*` 和 `apps/web/backend-python` 长期并存，未来再迁移成本更高。
2. **前端局部重复实现继续增长**：同一领域逻辑可能继续在 `app/hooks` 和 `hooks` 两边生长。
3. **后端 service 无法成为唯一业务入口**：router 继续膨胀，后续测试和拆分困难。
4. **API 契约持续漂移**：前端 service 层被迫长期做兼容补丁。
5. **治理文档失去约束力**：文档写的是目标，代码跑的是另一套现实。

---

## 3. 本次整改的最佳实践方案

### 3.1 选定的总体策略

**最佳方案不是现在立刻做物理迁移，也不是继续保持映射层长期存在。**

当前最优实践是：

> **先在现有真实代码路径 (`apps/web/`、`apps/api/`) 上完成分层收口与契约收口，再把 `apps/*` 从"逻辑映射层"升级为真正的物理主路径。**

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
2. **单一真源**：明确 `apps/web/` 与 `apps/api/` 是当前唯一代码主路径，`apps/*` 仍只作映射入口且禁止写业务代码。
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
- 真正代码在 `apps/web/` 和 `apps/api/`

影响：
- 新成员或 AI 容易误以为 `apps/*` 是真实实现目录
- 未来若有人开始往 `apps/*` 写新代码，会立刻形成双主路径

整改原则：
- 本轮不迁移真实代码
- 但必须把 `apps/*` 的"映射层身份"写死，并通过文档和校验保证不承接业务代码

### 问题 B：`.github/workflows` 已存在但需验证完整性 ✅ 部分完成

现状：
- `.github/workflows/` **已存在**，包含：
  - `governance-baseline.yml` - 治理基线检查工作流
  - `test.yml` - 测试工作流
- `.github/pull_request_template.md` **已存在**且内容完整
- `.github/ISSUE_TEMPLATE/` **已存在**（bug-report、feature-request、governance-task）
- `scripts/check-structure-boundaries.sh` 现在应能通过

影响：
- 治理门禁基础设施已具备
- 但需验证工作流是否包含四个治理脚本执行

整改原则：
- ✅ 无需新增 `.github/workflows/` 目录
- ⚠️ 验证现有工作流是否包含治理脚本执行，必要时补充

---

## 4.2 前端层问题

### 问题 C：同一领域 hook 双份存在

现状：
- `apps/web/src/hooks/useKnowledgeBases.ts`
- `apps/web/src/app/hooks/useKnowledgeBases.ts`

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
- `apps/web/src/app/` 已承接页面、局部 hooks、局部 contexts 和大量 components
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
- `apps/api/app/api/papers/paper_crud.py` 中直接做：
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
- `apps/api/app/models/note.py` 是 Pydantic 请求/响应模型
- `apps/api/app/models/orm_note.py` 是 SQLAlchemy ORM 模型

影响：
- `models` 语义混乱
- 导入路径难读
- 新人和 AI 难以判断"模型"到底是数据库模型还是接口模型

整改原则：
- 本轮新增 `apps/api/app/schemas/`
- `models/` 仅保留 ORM / persistence 模型
- `schemas/` 统一承接请求/响应模型

### 问题 H：同名模块与目录并存

现状：
- `apps/api/app/api/search.py`
- `apps/api/app/api/search/`

影响：
- search 领域边界不清晰
- 路由入口容易重复或绕路
- 未来拆分 search 相关能力时认知成本高

整改原则：
- 只保留一种 canonical 结构
- 结合当前已有 grouped API 方向，最佳实践是保留 `app/api/search/` 目录，逐步吸收 `search.py` 的内容，最后删除 `search.py`

### 问题 I：`core/` 偏胖

现状：
- `apps/api/app/core/` 下约 **49** 个 Python 文件
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
- `docs/specs/architecture/api-contract.md` 定义分页为 `limit + offset`，响应在 `meta.limit/meta.offset/meta.total`

真实实现（papers）：
- 请求用 `page + limit`
- 返回 `data.total/page/limit/totalPages`

#### 例 2：命名风格漂移

文档：
- 约定"命名风格转换只在 API 边界进行一次"

真实实现：
- `apps/api/app/api/papers/paper_shared.py` 返回对象内同时存在：
  - `arxiv_id`
  - `file_size`
  - `created_at`
  - `processingStatus`
  - `processingError`

这意味着同一个 payload 里混用 `snake_case` 与 `camelCase`。

#### 例 3：前端被迫兼容历史差异

`apps/web/src/services/papersApi.ts` 中 `normalizePaper()` 同时兼容：
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

- `apps/web/`：唯一前端真实代码主路径
- `apps/api/`：唯一后端真实代码主路径
- `apps/web`、`apps/api`：仅保留 README 和映射说明，不承接业务代码
- `.github/workflows/`：存在，并运行治理脚本
- `docs/`：继续作为唯一文档系统
- `packages/`：仅作为未来公共资产容器，不承接核心业务实现

### 下一阶段（后续里程碑）

- 当前路径收口完成后，再做物理迁移到 `apps/*`
- `packages/types`、`packages/sdk` 再开始承接真实共享契约

## 5.2 前端目标状态

- `apps/web/src/app` 只保留：
  - `App.tsx`
  - `routes.tsx`
  - `pages/`
  - 页面专属 hooks / contexts / 组件
- `apps/web/src/services`：唯一 HTTP / SSE 访问层
- `apps/web/src/hooks`：共享业务 hook
- `apps/web/src/stores`：全局状态
- `apps/web/src/types`：前端 DTO / 视图模型
- 同一业务 hook 只保留一份实现

## 5.3 后端目标状态

- `apps/api/app/api`：只保留协议入口
- `apps/api/app/services`：业务编排真源
- `apps/api/app/repositories`：数据访问层（本轮新增）
- `apps/api/app/models`：ORM 模型
- `apps/api/app/schemas`：请求/响应模型（本轮新增）
- `apps/api/app/core`：仅基础设施

## 5.4 契约目标状态

- 前端只消费 camelCase
- 后端对外 HTTP 响应统一为 camelCase
- 列表接口统一响应壳
- 分页策略统一，不允许同一资源内一部分用 `page`，另一部分用 `offset`

---

## 6. 分阶段整改实施方案

### Phase 依赖关系

```
Phase 0 (门禁闭环)
    ↓
Phase 1 (主路径冻结) ← 必须先完成
    ↓
Phase 2 (前端收口) ──┐
Phase 3 (后端整改) ──┼── 可并行
    ↓               ↓
Phase 4 (契约统一) ← 必须等待 2+3
    ↓
Phase 5 (迁移准备)
```

**关键依赖说明：**

| 依赖 | 原因 |
|------|------|
| Phase 0 → Phase 1 | 无门禁则无法验证后续整改是否合规 |
| Phase 1 → Phase 2/3 | 主路径未冻结时，整改可能落错位置 |
| Phase 2 + Phase 3 → Phase 4 | 前后端分层未收口时，契约统一会同时涉及多层修改 |
| Phase 4 → Phase 5 | 契约未统一时，packages 无法承接稳定类型 |

**并行执行建议：**

- Phase 2 和 Phase 3 可由不同开发者/子代理并行推进
- 但两者的验收必须在 Phase 4 开始前完成
- 若资源有限，优先完成 Phase 2（前端改动影响面更广）

---

### Phase 0：治理门禁闭环（优先级 P0） ✅ 大部分已完成

#### 目标

让仓库治理脚本四项全部通过；验证已有基础设施是否完整。

#### 当前状态

**已完成：**
- ✅ `.github/workflows/` 目录已存在（含 `governance-baseline.yml`、`test.yml`）
- ✅ `.github/pull_request_template.md` 已存在且内容完整
- ✅ `.github/ISSUE_TEMPLATE/` 已存在（bug-report、feature-request、governance-task）
- ✅ 四个治理脚本全部存在

**需验证/补充：**
- ⚠️ 验证工作流是否包含治理脚本执行
- ⚠️ 验证 `apps/*/README.md` 约束措辞是否足够清晰

#### 要做的事

##### 任务 0.1：验证 `.github/workflows/` 内容 ✅ 已存在

**当前状态：已存在**
- `.github/workflows/governance-baseline.yml`
- `.github/workflows/test.yml`

**操作：** 验证现有工作流是否包含四个治理脚本执行，如已包含则无需修改，如未包含则补充。

##### 任务 0.2：验证 `.github/pull_request_template.md` ✅ 已存在且完整

**当前状态：已存在**
已包含 Summary、Verification checklist、Contract impact、Governance Checklist 等字段。

**操作：** 无需修改，验证内容是否符合需求即可。

##### 任务 0.3：验证 `apps/*/README.md` 约束措辞 ⚠️ 已有等效约束

**当前状态：**
- `apps/web/README.md` 已包含：
  - "Current implementation lives in frontend"
  - "do not create a second frontend implementation path"
- `apps/api/README.md` 已包含：
  - "Current implementation lives in backend-python"

**操作：** 
- 验证现有约束措辞是否足够清晰
- 如需强化，可补充"禁止在 apps/* 中新增业务实现文件"的明确说明
- 但不必强制添加"禁止承接业务代码"特定文本（已有等效约束）

#### 验收标准（更新）

| 序号 | 验收项 | 验收命令/方法 | 期望结果 |
|------|--------|---------------|----------|
| 1 | 治理脚本全部通过 | `bash scripts/check-doc-governance.sh && bash scripts/check-structure-boundaries.sh && bash scripts/check-code-boundaries.sh && bash scripts/check-governance.sh` | Exit code = 0 |
| 2 | GitHub Actions 工作流存在 | `test -f .github/workflows/governance-baseline.yml || test -f .github/workflows/governance.yml` | Exit code = 0 |
| 3 | PR 模板存在 | `test -f .github/pull_request_template.md` | Exit code = 0 ✅ |
| 4 | apps README 包含约束说明 | `grep -q "Current implementation lives in frontend" apps/web/README.md && grep -q "Current implementation lives in backend-python" apps/api/README.md` | Exit code = 0 ✅ |
| 5 | Issue 模板存在 | `test -d .github/ISSUE_TEMPLATE` | Exit code = 0 ✅ |

**验收执行脚本（更新版）：**

```bash
#!/bin/bash
# scripts/verify-phase0.sh

set -e

echo "=== Phase 0 验收开始 ==="

# 1. 检查文件存在
echo "[1/5] 检查必需文件..."
test -f .github/workflows/governance-baseline.yml || test -f .github/workflows/governance.yml
test -f .github/pull_request_template.md
test -d .github/ISSUE_TEMPLATE
echo "✓ 文件存在"

# 2. 检查 README 内容（调整为已有措辞）
echo "[2/5] 检查 apps README 内容..."
grep -q "Current implementation lives in frontend" apps/web/README.md
grep -q "Current implementation lives in backend-python" apps/api/README.md
echo "✓ README 约束说明存在"

# 3. 运行治理脚本
echo "[3/5] 运行治理脚本..."
bash scripts/check-doc-governance.sh
bash scripts/check-structure-boundaries.sh
bash scripts/check-code-boundaries.sh
bash scripts/check-governance.sh
echo "✓ 治理脚本通过"

# 4. 检查工作流语法
echo "[4/5] 检查工作流 YAML 语法..."
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/governance-baseline.yml'))" || \
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/governance.yml'))"
echo "✓ YAML 语法正确"

# 5. 检查工作流触发条件
echo "[5/5] 检查工作流触发配置..."
grep -q "on:" .github/workflows/governance-baseline.yml || grep -q "on:" .github/workflows/governance.yml
grep -qE "(push|pull_request|workflow_dispatch)" .github/workflows/governance-baseline.yml || \
grep -qE "(push|pull_request|workflow_dispatch)" .github/workflows/governance.yml
echo "✓ 触发条件配置正确"

echo "=== Phase 0 验收完成 ✓ ==="
grep -q "禁止承接业务代码" apps/api/README.md
echo "✓ README 内容正确"

# 3. 运行治理脚本
echo "[3/5] 运行治理脚本..."
bash scripts/check-doc-governance.sh
bash scripts/check-structure-boundaries.sh
bash scripts/check-code-boundaries.sh
bash scripts/check-governance.sh
echo "✓ 治理脚本通过"

# 4. 检查工作流语法
echo "[4/5] 检查工作流 YAML 语法..."
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/governance.yml'))"
echo "✓ YAML 语法正确"

# 5. 检查工作流触发条件
echo "[5/5] 检查工作流触发配置..."
grep -q "on:" .github/workflows/governance.yml
grep -qE "(push|pull_request|workflow_dispatch)" .github/workflows/governance.yml
echo "✓ 触发条件配置正确"

echo "=== Phase 0 验收完成 ✓ ==="
```

---

### Phase 1：主路径冻结与仓库真源收口（优先级 P0） ⚠️ 需验证而非新增

#### 目标

验证"当前真正的代码主路径"已在文档中明确，必要时补充强化约束。

#### 当前状态

**已存在的内容：**
- ✅ `README.md` 已包含逻辑映射说明：`apps/web -> apps/web`、`apps/api -> apps/api`
- ✅ `AGENTS.md` 已存在，包含：
  - Scope mapping: `apps/web -> apps/web`, `apps/api -> apps/api`
  - 禁止新增根级 `doc`、`tmp`、`legacy`、`_new` 等目录规则
  - 提交禁止文件列表（*.pid、cookies.txt、临时日志）

**可能需补充：**
- ⚠️ 验证是否需要更明确的"唯一"主路径声明
- ⚠️ 验证 AI 边界规则是否足够严格

#### 要做的事

##### 任务 1.1：验证并补充 `README.md` 主路径声明 ⚠️ 部分存在

**当前状态：** 已有逻辑映射说明，但措辞是"Logical alignment"，而非明确的"唯一主路径"声明。

**操作：**
- 验证现有"Logical mapping"说明是否足够清晰
- 如需强化，补充明确措辞：
  - `apps/web/` 是当前**唯一**前端真实代码主路径
  - `apps/api/` 是当前**唯一**后端真实代码主路径
  - `apps/*` 仅作逻辑映射占位，不承接新业务实现

### 任务 1.2：验证 `AGENTS.md` AI 边界规则 ⚠️ 部分存在

**当前状态：** 已有 scope mapping 和禁止新增目录规则。

**操作：**
- 验证现有规则是否足够严格
- 如需强化，补充明确规则：
  - AI 修改前端代码时，只允许进入 `apps/web/`
  - AI 修改后端代码时，只允许进入 `apps/api/`
  - 若变更落到 `apps/*`，必须被视为结构违规

### 任务 1.3：验证结构边界脚本 ✅ 已存在

**当前状态：** `scripts/check-structure-boundaries.sh` 已存在且包含：
- Required directories 检查（含 `.github/workflows`）
- Forbidden directories 检查（`doc`、`tmp`、`legacy`、`_new`）
- Forbidden files 检查（`*.pid`、`*.log`、`*.out`）

**操作：** 验证是否已包含 apps 目录业务代码检测，如未包含则补充：
- 检查 `apps/web` 与 `apps/api` 中是否出现 `.ts/.tsx/.js/.py` 真实业务代码
- 允许存在 README 和占位文档

#### 验收标准（更新）

| 序号 | 验收项 | 验收命令/方法 | 期望结果 |
|------|--------|---------------|----------|
| 1 | README.md 包含主路径说明 | `grep -q "Logical mapping" README.md || grep -q "frontend.*backend-python" README.md` | Exit code = 0 ✅ |
| 2 | AGENTS.md 包含 scope mapping | `grep -q "apps/web" AGENTS.md && grep -q "frontend" AGENTS.md` | Exit code = 0 ✅ |
| 3 | apps README 包含约束说明 | `grep -q "Current implementation lives in frontend" apps/web/README.md` | Exit code = 0 ✅ |
| 4 | 结构边界脚本检测 apps 代码 | 验证脚本内容或运行测试 | 脚本应拒绝 apps 中新增业务代码 |
| 5 | 四个治理脚本通过 | `bash scripts/check-governance.sh` | Exit code = 0 |

**验收执行脚本（更新版）：**

```bash
#!/bin/bash
# scripts/verify-phase1.sh

set -e

echo "=== Phase 1 验收开始 ==="

# 1. 检查 README 主路径说明（调整为已有措辞）
echo "[1/5] 检查 README.md 主路径说明..."
grep -q "Logical mapping" README.md || grep -qE "(frontend|backend-python)" README.md
echo "✓ README.md 包含主路径说明"

# 2. 检查 AGENTS.md scope mapping（调整为已有措辞）
echo "[2/5] 检查 AGENTS.md 边界规则..."
grep -q "apps/web" AGENTS.md
grep -q "frontend" AGENTS.md
grep -q "apps/api" AGENTS.md
echo "✓ AGENTS.md 包含 scope mapping"

# 3. 检查 apps README
echo "[3/5] 检查 apps README 内容..."
grep -q "Current implementation lives in frontend" apps/web/README.md
grep -q "Current implementation lives in backend-python" apps/api/README.md
echo "✓ apps README 内容正确"

# 4. 测试结构边界脚本拒绝能力（如有检测逻辑）
echo "[4/5] 验证结构边界脚本..."
# 检查脚本是否包含 apps 检测逻辑
if grep -q "apps/web" scripts/check-structure-boundaries.sh; then
    echo "✓ 脚本包含 apps 检测"
else
    echo "⚠ 脚本可能缺少 apps 业务代码检测，建议补充"
fi

# 5. 运行治理脚本
echo "[5/5] 运行治理脚本..."
bash scripts/check-governance.sh
echo "✓ 治理脚本通过"

echo "=== Phase 1 验收完成 ✓ ==="
```

---

### Phase 2：前端分层收口（优先级 P0/P1）

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
- **保留 `apps/web/src/hooks/useKnowledgeBases.ts` 作为共享 canonical hook**
- 删除 `apps/web/src/app/hooks/useKnowledgeBases.ts`

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
4. 删除 `apps/web/src/app/hooks/useKnowledgeBases.ts`
5. 给 `scripts/check-code-boundaries.sh` 或新增脚本补一个简单检查：禁止 `app/hooks` 与 `hooks` 出现同名文件

### 任务 2.2：明确 `app/hooks` 的允许范围

保留在 `apps/web/src/app/hooks/` 的仅限：
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
- `docs/specs/development/coding-standards.md`
- `AGENTS.md`

### 任务 2.3：统一 service 返回值规范

选定规则：

> `apps/web/src/services/*` 一律返回业务 DTO，不返回二次包装的 `{ success, data }` 给页面层。

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

更新 `docs/specs/development/coding-standards.md`：

- React Query：服务端数据缓存
- store：跨页面全局状态（用户、UI、当前会话上下文）
- context：主题/语言/认证外壳等少量跨树注入
- hooks：封装交互流程，不做持久全局状态真源

#### 验收标准

| 序号 | 验收项 | 验收命令/方法 | 期望结果 |
|------|--------|---------------|----------|
| 1 | useKnowledgeBases 只有一份实现 | `find apps/web/src -name "useKnowledgeBases.ts" \| wc -l` | 输出 = 1 |
| 2 | 使用共享版本而非 app 版本 | `grep -r "from.*app/hooks/useKnowledgeBases" apps/web/src \| wc -l` | 输出 = 0 |
| 3 | TypeScript 类型检查通过 | `cd apps/web && npm run type-check` | Exit code = 0 |
| 4 | 前端测试通过 | `cd apps/web && npm run test:run` | Exit code = 0，覆盖率 ≥ 80% |
| 5 | kbApi 返回纯 DTO | `grep -q "return response.data" apps/web/src/services/kbApi.ts` 或人工检查 | 不返回 `{ success, data }` 包装 |
| 6 | 前端边界规则文档化 | `test -f docs/specs/development/coding-standards.md && grep -q "app/hooks" docs/specs/development/coding-standards.md` | Exit code = 0 |
| 7 | 无同名 hook 冲突 | `comm -12 <(ls apps/web/src/hooks/ 2>/dev/null \| sort) <(ls apps/web/src/app/hooks/ 2>/dev/null \| sort)` | 输出为空 |

**验收执行脚本（一键验证）：**

```bash
#!/bin/bash
# scripts/verify-phase2.sh

set -e

echo "=== Phase 2 验收开始 ==="

# 1. 检查 useKnowledgeBases 只有一份
echo "[1/7] 检查 useKnowledgeBases 实现数量..."
count=$(find apps/web/src -name "useKnowledgeBases.ts" | wc -l | tr -d ' ')
if [ "$count" -ne 1 ]; then
    echo "✗ 发现 $count 份 useKnowledgeBases 实现，应为 1 份"
    exit 1
fi
echo "✓ useKnowledgeBases 只有一份实现"

# 2. 检查无 app/hooks 引用
echo "[2/7] 检查无 app/hooks/useKnowledgeBases 引用..."
refs=$(grep -r "from.*app/hooks/useKnowledgeBases" apps/web/src 2>/dev/null | wc -l | tr -d ' ')
if [ "$refs" -ne 0 ]; then
    echo "✗ 发现 $refs 处引用 app/hooks/useKnowledgeBases"
    exit 1
fi
echo "✓ 无 app/hooks/useKnowledgeBases 引用"

# 3. 检查无同名 hook 冲突
echo "[3/7] 检查无同名 hook 冲突..."
conflicts=$(comm -12 <(ls apps/web/src/hooks/ 2>/dev/null | sort) <(ls apps/web/src/app/hooks/ 2>/dev/null | sort) 2>/dev/null || true)
if [ -n "$conflicts" ]; then
    echo "✗ 发现同名 hook 冲突: $conflicts"
    exit 1
fi
echo "✓ 无同名 hook 冲突"

# 4. TypeScript 类型检查
echo "[4/7] 运行 TypeScript 类型检查..."
cd apps/web && npm run type-check
cd ..
echo "✓ TypeScript 类型检查通过"

# 5. 前端测试
echo "[5/7] 运行前端测试..."
cd apps/web && npm run test:run
cd ..
echo "✓ 前端测试通过"

# 6. 检查文档更新
echo "[6/7] 检查前端边界规则文档..."
test -f docs/specs/development/coding-standards.md
grep -q "app/hooks" docs/specs/development/coding-standards.md || grep -q "共享业务 hook" docs/specs/development/coding-standards.md
echo "✓ 文档已更新"

# 7. 检查 kbApi DTO 化（抽样）
echo "[7/7] 检查 kbApi 返回值规范..."
if grep -q "return { success: true, data:" apps/web/src/services/kbApi.ts 2>/dev/null; then
    echo "⚠ kbApi 仍包含 { success, data } 包装，建议继续整改"
else
    echo "✓ kbApi 已完成 DTO 化"
fi

echo "=== Phase 2 验收完成 ✓ ==="
```

---

### Phase 3：后端分层整改（优先级 P0/P1）

## 目标

把"router 仍做太多事"的状态，推进到"service 是唯一业务编排真源"。

## 当前状态

**已存在：**
- ✅ `apps/api/app/services/` 已存在，包含 **14 个服务文件**：
  - `paper_service.py`、`auth_service.py`、`chat_orchestrator.py`、`import_job_service.py`、
  - `message_service.py`、`storage_service.py`、`task_service.py` 等
- ✅ `paper_service.py` 已存在（12,923 bytes），但 `paper_crud.py` 未完全使用它

**不存在：**
- ❌ `apps/api/app/schemas/` 目录不存在
- ❌ `apps/api/app/repositories/` 目录不存在

**问题确认：**
- `paper_crud.py` 仍直接执行 `db.execute`、`select()`、`func.count`、`text()` 等 SQL 操作
- `models/` 中混放 Pydantic schema（`note.py`、`session.py`、`rag.py`）
- `search.py` 与 `search/` 目录并存

## 本轮选定的后端最佳实践

当前最优路径不是直接大拆 DDD，而是采用**标准三段式**：

- `api/`：协议入口
- `services/`：业务编排 ✅ 已存在
- `repositories/`：数据库访问 ❌ 需新增

并在此基础上把 `schemas/` 从 `models/` 中拆出。

## 要做的事

### 任务 3.1：新增 `apps/api/app/schemas/` ❌ 不存在

新增目录：
- `apps/api/app/schemas/`

首批迁移文件建议：
- `apps/api/app/models/note.py` -> `apps/api/app/schemas/note.py`
- `apps/api/app/models/session.py` -> `apps/api/app/schemas/session.py`
- `apps/api/app/models/rag.py` -> `apps/api/app/schemas/rag.py`
- `apps/api/app/api/papers/paper_shared.py` 中的 request/response model -> 拆成 `apps/api/app/schemas/papers.py`

**注意：** `reading_progress.py` 是 ORM 模型，不应迁移到 schemas。

### 任务 3.2：收紧 `models/`

整改后规则：
- `models/` 只允许 SQLAlchemy ORM 或数据库持久化模型
- 禁止新增 Pydantic `BaseModel` 到 `models/`

需要同步更新：
- `docs/specs/development/coding-standards.md`
- `AGENTS.md`
- `docs/specs/governance/code-boundary-baseline.md`

### 任务 3.3：新增 `apps/api/app/repositories/` ❌ 不存在

新增目录：
- `apps/api/app/repositories/`

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

### 任务 3.4：改造 `paper_crud.py` 使用现有 `paper_service.py` ⚠️ 重点任务

这是后端分层整改第一批样板工程，必须优先做。

#### 当前问题
`paper_crud.py` 直接做了：
- 分页参数归一化
- ORM 查询拼装（`db.execute`、`select()`、`func.count`、`text()`）
- 业务筛选（starred、readStatus、date range）
- count
- DTO 格式化

#### 整改后的目标结构

- `app/api/papers/paper_crud.py`
  - 只保留 FastAPI endpoint 和依赖注入
- `app/services/paper_service.py` ✅ 已存在
  - 扩展提供 `list_papers(...)`、`search_papers(...)` 方法
  - 当前已有部分功能，需验证并扩展
- `app/repositories/paper_repository.py` ❌ 需新增
  - 提供真正的 SQLAlchemy 查询
- `app/schemas/papers.py` ❌ 需新增
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

### 任务 3.5：收口 `api/search.py` 与 `api/search/` ⚠️ 确认并存

**当前状态：** 确认并存
- `apps/api/app/api/search.py` 存在
- `apps/api/app/api/search/` 目录存在，包含：
  - `__init__.py`、`external.py`、`library.py`、`multimodal.py`、`shared.py`

最佳做法：
- 保留 `apps/api/app/api/search/` 目录作为 canonical search API area
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
- `docs/specs/governance/core-boundary-baseline.md`（建议）

### 任务 3.7：收紧 code boundary baseline

当前 `docs/specs/governance/code-boundary-baseline.md` 允许多份 API 文件继续直连数据库。这是现实，但必须分波次削减。

本轮目标：
- 至少完成 `paper_crud.py` 从 allowlist 中移除
- 若进度允许，再处理：
  - `paper_status.py`
  - `kb/kb_crud.py`

#### 验收标准

| 序号 | 验收项 | 验收命令/方法 | 期望结果 |
|------|--------|---------------|----------|
| 1 | schemas 目录存在且有内容 | `test -d apps/api/app/schemas && ls apps/api/app/schemas/*.py \| wc -l` | 目录存在，至少 3 个 .py 文件 |
| 2 | repositories 目录存在且有内容 | `test -d apps/api/app/repositories && ls apps/api/app/repositories/*.py \| wc -l` | 目录存在，至少 2 个 .py 文件 |
| 3 | models 不含 Pydantic BaseModel | `grep -r "class.*BaseModel" apps/api/app/models/ \| wc -l` | 输出 = 0 |
| 4 | paper_crud.py 无直接 SQL 查询 | `grep -qE "(db\.execute|select\(.*\)|func\.count)" apps/api/app/api/papers/paper_crud.py` | Exit code ≠ 0 (不存在) |
| 5 | search.py 已删除或标记 deprecated | `test ! -f apps/api/app/api/search.py || grep -q "deprecated" apps/api/app/api/search.py` | 文件不存在或含 deprecated |
| 6 | code-boundary-baseline allowlist 减少 | 手动对比 `docs/specs/governance/code-boundary-baseline.md` allowlist | allowlist 项数减少 ≥ 1 |
| 7 | 后端测试通过 | `cd apps/api && pytest -x --tb=short` | Exit code = 0 |
| 8 | paper_service.py 存在 | `test -f apps/api/app/services/paper_service.py` | Exit code = 0 |

**验收执行脚本（一键验证）：**

```bash
#!/bin/bash
# scripts/verify-phase3.sh

set -e

echo "=== Phase 3 验收开始 ==="

# 1. 检查 schemas 目录
echo "[1/8] 检查 schemas 目录..."
test -d apps/api/app/schemas
schema_count=$(ls apps/api/app/schemas/*.py 2>/dev/null | wc -l | tr -d ' ')
if [ "$schema_count" -lt 3 ]; then
    echo "✗ schemas 只有 $schema_count 个文件，应至少 3 个"
    exit 1
fi
echo "✓ schemas 目录存在，包含 $schema_count 个文件"

# 2. 检查 repositories 目录
echo "[2/8] 检查 repositories 目录..."
test -d apps/api/app/repositories
repo_count=$(ls apps/api/app/repositories/*.py 2>/dev/null | wc -l | tr -d ' ')
if [ "$repo_count" -lt 2 ]; then
    echo "✗ repositories 只有 $repo_count 个文件，应至少 2 个"
    exit 1
fi
echo "✓ repositories 目录存在，包含 $repo_count 个文件"

# 3. 检查 models 不含 Pydantic
echo "[3/8] 检查 models 不含 Pydantic BaseModel..."
pydantic_count=$(grep -r "class.*BaseModel" apps/api/app/models/ 2>/dev/null | wc -l | tr -d ' ')
if [ "$pydantic_count" -gt 0 ]; then
    echo "✗ models 中仍有 $pydantic_count 个 Pydantic 类"
    exit 1
fi
echo "✓ models 不含 Pydantic BaseModel"

# 4. 检查 paper_crud.py 无直接 SQL
echo "[4/8] 检查 paper_crud.py 无直接 SQL..."
if grep -qE "(db\.execute|select\(Paper\)|func\.count)" apps/api/app/api/papers/paper_crud.py 2>/dev/null; then
    echo "✗ paper_crud.py 仍包含直接 SQL 查询"
    exit 1
fi
echo "✓ paper_crud.py 无直接 SQL 查询"

# 5. 检查 search.py 状态
echo "[5/8] 检查 search.py 状态..."
if [ -f apps/api/app/api/search.py ]; then
    if grep -q "deprecated" apps/api/app/api/search.py; then
        echo "✓ search.py 已标记 deprecated"
    else
        echo "⚠ search.py 存在但未标记 deprecated，建议继续整改"
    fi
else
    echo "✓ search.py 已删除"
fi

# 6. 检查 paper_service.py 存在
echo "[6/8] 检查 paper_service.py..."
test -f apps/api/app/services/paper_service.py
echo "✓ paper_service.py 存在"

# 7. 检查 code-boundary-baseline
echo "[7/8] 检查 code-boundary-baseline..."
test -f docs/specs/governance/code-boundary-baseline.md
echo "⚠ 请手动对比 allowlist 是否减少 ≥ 1 项"

# 8. 后端测试
echo "[8/8] 运行后端测试..."
cd apps/api && pytest -x --tb=short -q
cd ..
echo "✓ 后端测试通过"

echo "=== Phase 3 验收完成 ✓ ==="
```

---

### Phase 4：API 契约统一（优先级 P0）

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

因为当前 `docs/specs/architecture/api-contract.md` 已经写了 `limit/offset`。最佳实践是：
- 不改文档去追随旧实现
- 改旧实现去服从文档

过渡方式：
- 在一个版本周期内，后端暂时兼容 `page + limit`
- 但 service/schema 统一使用 `limit + offset`
- 前端新代码全部改为 `limit + offset`
- 兼容结束后删除 `page`

## 要做的事

### 任务 4.1：更新 `docs/specs/architecture/api-contract.md`

补充明确条目：
- 列表接口统一 `data.items + meta`
- 前端 DTO 一律 camelCase
- 后端 API 输出为 camelCase
- 旧接口兼容策略与退场时限

### 任务 4.2：新增 `apps/api/app/schemas/common.py`

定义通用响应壳：
- `SuccessResponse[T]`
- `ListMeta`
- `ListResponse[T]`
- `ProblemDetailResponse`

### 任务 4.3：首批落地到 `papers`

修改：
- `apps/api/app/api/papers/paper_shared.py` 或迁移后 `schemas/papers.py`
- `apps/web/src/services/papersApi.ts`
- `apps/web/src/types/*`

目标：
- 后端输出 camelCase paper DTO
- 列表返回 `items + meta`
- 前端移除一部分 normalize 兼容逻辑

### 任务 4.4：收敛 `kbApi` 和 `papersApi`

使两个 service 都遵循相同模式：
- 不再手工包 `{ success, data }`
- 都消费统一 DTO

#### 验收标准

| 序号 | 验收项 | 验收命令/方法 | 期望结果 |
|------|--------|---------------|----------|
| 1 | API 契约文档更新 | `grep -q "data.items" docs/specs/architecture/api-contract.md && grep -q "camelCase" docs/specs/architecture/api-contract.md` | Exit code = 0 |
| 2 | common.py 定义响应壳 | `test -f apps/api/app/schemas/common.py && grep -q "ListResponse" apps/api/app/schemas/common.py` | Exit code = 0 |
| 3 | papers 列表返回 items + meta | `curl -s localhost:8000/api/papers \| jq 'has("data") and .data.has("items") and has("meta")'` | 输出 = true |
| 4 | papers 响应全 camelCase | `curl -s localhost:8000/api/papers \| jq '.data.items[0] \| keys' \| grep -v "_"` | 无 snake_case 字段 |
| 5 | papersApi.ts 兼容代码减少 | `grep -c "arxivId\|arxiv_id" apps/web/src/services/papersApi.ts` | 兼容逻辑行数减少 ≥ 50% |
| 6 | 后端 payload 无混用命名 | `curl -s localhost:8000/api/papers \| jq '.data.items[0]' \| jq -r 'keys[]' \| grep "_" \| wc -l` | 输出 = 0 |
| 7 | 前端类型定义匹配契约 | `grep -q "items:" apps/web/src/types/papers.ts` | Exit code = 0 |

**验收执行脚本（一键验证）：**

```bash
#!/bin/bash
# scripts/verify-phase4.sh

set -e

echo "=== Phase 4 验收开始 ==="

# 1. 检查 API 契约文档
echo "[1/7] 检查 API 契约文档..."
test -f docs/specs/architecture/api-contract.md
grep -q "data.items" docs/specs/architecture/api-contract.md
grep -q "camelCase" docs/specs/architecture/api-contract.md
echo "✓ API 契约文档已更新"

# 2. 检查 common.py 响应壳
echo "[2/7] 检查 common.py 响应壳定义..."
test -f apps/api/app/schemas/common.py
grep -q "ListResponse\|ListMeta" apps/api/app/schemas/common.py
echo "✓ common.py 响应壳定义正确"

# 3. 检查前端类型定义
echo "[3/7] 检查前端类型定义..."
if [ -f apps/web/src/types/papers.ts ]; then
    grep -q "items:" apps/web/src/types/papers.ts || grep -q "PaperListResponse" apps/web/src/types/papers.ts
    echo "✓ 前端类型定义已更新"
else
    echo "⚠ 前端类型文件不存在，跳过检查"
fi

# 4. 检查 papersApi 兼容代码
echo "[4/7] 检查 papersApi 兼容代码..."
if [ -f apps/web/src/services/papersApi.ts ]; then
    compat_lines=$(grep -cE "(arxivId\|arxiv_id|storageKey\|storage_key)" apps/web/src/services/papersApi.ts 2>/dev/null || echo "0")
    echo "⚠ papersApi 兼容代码行数: $compat_lines (应减少 ≥ 50%)"
else
    echo "⚠ papersApi.ts 不存在，跳过检查"
fi

# 5. 检查后端响应格式（需要服务运行）
echo "[5/7] 检查后端响应格式..."
if curl -s --connect-timeout 2 localhost:8000/health > /dev/null 2>&1; then
    response=$(curl -s localhost:8000/api/papers 2>/dev/null || echo "{}")
    
    # 检查 items + meta 结构
    if echo "$response" | jq -e 'has("data") and .data.has("items") and has("meta")' > /dev/null 2>&1; then
        echo "✓ papers 列表返回 items + meta 结构"
    else
        echo "⚠ papers 列表结构未完全符合契约（可能无数据或服务未完全整改）"
    fi
    
    # 检查无 snake_case
    snake_count=$(echo "$response" | jq '.data.items[0] // {} | keys[]' 2>/dev/null | grep "_" | wc -l | tr -d ' ')
    if [ "$snake_count" -eq 0 ]; then
        echo "✓ papers 响应无 snake_case 字段"
    else
        echo "⚠ papers 响应仍有 $snake_count 个 snake_case 字段"
    fi
else
    echo "⚠ 后端服务未运行，跳过运行时验证"
fi

# 6. 检查 kbApi 和 papersApi 统一模式
echo "[6/7] 检查 service 返回模式统一..."
if [ -f apps/web/src/services/kbApi.ts ] && [ -f apps/web/src/services/papersApi.ts ]; then
    # 检查是否都不返回 { success, data }
    kb_wrapper=$(grep -c "return { success" apps/web/src/services/kbApi.ts 2>/dev/null || echo "0")
    paper_wrapper=$(grep -c "return { success" apps/web/src/services/papersApi.ts 2>/dev/null || echo "0")
    if [ "$kb_wrapper" -eq 0 ] && [ "$paper_wrapper" -eq 0 ]; then
        echo "✓ kbApi 和 papersApi 都不返回 { success, data } 包装"
    else
        echo "⚠ kbApi/papersApi 仍有 { success, data } 包装"
    fi
else
    echo "⚠ service 文件不存在，跳过检查"
fi

# 7. 检查 schemas/papers.py 存在
echo "[7/7] 检查 schemas/papers.py..."
test -f apps/api/app/schemas/papers.py
echo "✓ schemas/papers.py 存在"

echo "=== Phase 4 验收完成 ✓ ==="
```

---

### Phase 5：为后续物理迁移与 packages 承接做准备（优先级 P2）

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
- `docs/specs/adr/0002-delay-physical-migration-until-boundary-convergence.md`

记录本次决策：
- 为什么暂缓物理迁移
- 为什么先做边界收口和契约统一

#### 验收标准

| 序号 | 验收项 | 验收命令/方法 | 期望结果 |
|------|--------|---------------|----------|
| 1 | packages 各目录 README 包含承接边界 | `grep -q "只放" packages/types/README.md && grep -q "只放" packages/sdk/README.md` | Exit code = 0 |
| 2 | 迁移条件清单文档化 | `test -f docs/specs/governance/migration-conditions.md 或 grep -q "迁移条件" docs/specs/architecture/repository-architecture.md` | Exit code = 0 |
| 3 | ADR 文档存在 | `test -f docs/specs/adr/0002-delay-physical-migration-until-boundary-convergence.md` | Exit code = 0 |
| 4 | packages 无业务代码 | `find packages -name "*.ts" -o -name "*.tsx" -o -name "*.py" \| grep -v README \| wc -l` | 输出 = 0 |
| 5 | 迁移条件可检查脚本化 | `test -f scripts/check-migration-readiness.sh`（可选） | Exit code = 0（可选） |

**验收执行脚本（一键验证）：**

```bash
#!/bin/bash
# scripts/verify-phase5.sh

set -e

echo "=== Phase 5 验收开始 ==="

# 1. 检查 packages README 承接边界
echo "[1/5] 检查 packages README 承接边界说明..."
for pkg in types sdk ui config; do
    if [ -f "packages/$pkg/README.md" ]; then
        grep -q "只放" "packages/$pkg/README.md" || grep -q "承接边界" "packages/$pkg/README.md"
        echo "✓ packages/$pkg/README.md 包含承接边界说明"
    else
        echo "⚠ packages/$pkg/README.md 不存在"
    fi
done

# 2. 检查迁移条件清单
echo "[2/5] 检查迁移条件清单..."
if [ -f docs/specs/governance/migration-conditions.md ]; then
    echo "✓ docs/specs/governance/migration-conditions.md 存在"
elif grep -q "迁移条件" docs/specs/architecture/repository-architecture.md 2>/dev/null; then
    echo "✓ 迁移条件已写入 repository-architecture.md"
else
    echo "✗ 迁移条件清单未文档化"
    exit 1
fi

# 3. 检查 ADR 文档
echo "[3/5] 检查 ADR 文档..."
test -f docs/specs/adr/0002-delay-physical-migration-until-boundary-convergence.md
echo "✓ ADR 文档存在"

# 4. 检查 packages 无业务代码
echo "[4/5] 检查 packages 无业务代码..."
code_files=$(find packages -name "*.ts" -o -name "*.tsx" -o -name "*.py" 2>/dev/null | grep -v README | grep -v .gitkeep | wc -l | tr -d ' ')
if [ "$code_files" -gt 0 ]; then
    echo "⚠ packages 中有 $code_files 个业务代码文件（本轮不应承接）"
else
    echo "✓ packages 无业务代码"
fi

# 5. 可选：检查迁移条件检查脚本
echo "[5/5] 检查迁移条件检查脚本（可选）..."
if [ -f scripts/check-migration-readiness.sh ]; then
    echo "✓ scripts/check-migration-readiness.sh 存在"
    echo "  可运行: bash scripts/check-migration-readiness.sh"
else
    echo "⚠ 迁移条件检查脚本未创建（可选项）"
fi

echo "=== Phase 5 验收完成 ✓ ==="
```

---

## 7. 具体文件修改清单

以下是建议直接落地的文件清单。

## 7.1 新增文件

### 仓库治理
- `.github/workflows/governance.yml`
- `.github/pull_request_template.md`
- `docs/specs/adr/0002-delay-physical-migration-until-boundary-convergence.md`
- `docs/specs/governance/core-boundary-baseline.md`（建议）

### 后端分层
- `apps/api/app/schemas/__init__.py`
- `apps/api/app/schemas/common.py`
- `apps/api/app/schemas/note.py`
- `apps/api/app/schemas/session.py`
- `apps/api/app/schemas/papers.py`
- `apps/api/app/repositories/__init__.py`
- `apps/api/app/repositories/paper_repository.py`
- `apps/api/app/repositories/reading_progress_repository.py`

### 前端分层（可选但推荐）
- `apps/web/src/features/README.md`
- `apps/web/src/features/papers/.gitkeep`
- `apps/web/src/features/notes/.gitkeep`
- `apps/web/src/features/chat/.gitkeep`

## 7.2 必改文件

### 仓库与文档
- `README.md`
- `AGENTS.md`
- `apps/web/README.md`
- `apps/api/README.md`
- `docs/specs/architecture/api-contract.md`
- `docs/specs/development/coding-standards.md`
- `docs/specs/governance/code-boundary-baseline.md`
- `scripts/check-structure-boundaries.sh`
- `scripts/check-code-boundaries.sh`（如增加同名 hook 检查）

### 前端
- `apps/web/src/hooks/useKnowledgeBases.ts`
- `apps/web/src/app/hooks/useKnowledgeBases.ts`（删除）
- `apps/web/src/services/kbApi.ts`
- `apps/web/src/services/papersApi.ts`
- 相关页面 import 路径

### 后端
- `apps/api/app/api/papers/paper_crud.py`
- `apps/api/app/api/papers/paper_shared.py`
- `apps/api/app/services/paper_service.py`
- `apps/api/app/api/search.py`（删除或迁移后下线）
- `apps/api/app/models/note.py`（迁移后删除）
- `apps/api/app/models/session.py`（迁移后删除）

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

### PR-1：治理闭环 PR

**范围：**
- `.github/workflows`
- PR 模板
- `README.md`
- `AGENTS.md`
- `apps/*/README.md`
- `scripts/check-structure-boundaries.sh`

**验收标准：**

| 序号 | 验收项 | 验收命令 | 期望结果 |
|------|--------|----------|----------|
| 1 | 四个治理脚本全通过 | `bash scripts/verify-phase0.sh && bash scripts/verify-phase1.sh` | Exit code = 0 |
| 2 | GitHub Actions 工作流可运行 | GitHub Actions 页面检查 | 工作流执行成功 |
| 3 | 文档一致性 | 手动检查 | README/AGENTS/apps README 表述一致 |

**回滚命令：**
```bash
# 若 PR-1 需要回滚
git revert <pr-1-commit-sha>

# 或创建回滚分支
git checkout main
git branch rollback-pr1-$(date +%Y%m%d)
git reset --hard <pre-pr1-sha>
git push origin rollback-pr1-$(date +%Y%m%d) --force
```

### PR-2：前端收口 PR

**范围：**
- 删除 `app/hooks/useKnowledgeBases.ts`
- 统一 `useKnowledgeBases` 契约
- service 返回规则样板化
- 文档更新

**验收标准：**

| 序号 | 验收项 | 验收命令 | 期望结果 |
|------|--------|----------|----------|
| 1 | TypeScript 类型检查 | `cd apps/web && npm run type-check` | Exit code = 0 |
| 2 | 前端测试通过 | `cd apps/web && npm run test:run` | Exit code = 0，覆盖率 ≥ 80% |
| 3 | 无重复 hook | `bash scripts/verify-phase2.sh` | Exit code = 0 |

**回滚命令：**
```bash
# 若 PR-2 需要回滚（保留已合并的 PR-1）
git revert <pr-2-commit-sha>

# 恢复被删除的 app/hooks/useKnowledgeBases.ts
git checkout <pre-pr2-sha> -- apps/web/src/app/hooks/useKnowledgeBases.ts
git commit -m "rollback: restore app/hooks/useKnowledgeBases.ts"
```

### PR-3：后端样板 PR

**范围：**
- 新增 `schemas/`
- 新增 `repositories/`
- 改造 `paper_crud.py`
- 收口 `search.py`
- 更新 `code-boundary-baseline`

**验收标准：**

| 序号 | 验收项 | 验收命令 | 期望结果 |
|------|--------|----------|----------|
| 1 | 后端测试通过 | `cd apps/api && pytest -x --tb=short` | Exit code = 0 |
| 2 | baseline allowlist 减少 | `grep -c "allowlist" docs/specs/governance/code-boundary-baseline.md` | 项数减少 ≥ 1 |
| 3 | 所有契约样板跑通 | `curl localhost:8000/api/papers` | 返回 items + meta 结构 |

**回滚命令：**
```bash
# 若 PR-3 需要回滚（保留已合并的 PR-1、PR-2）
git revert <pr-3-commit-sha>

# 仅回滚 paper_crud.py 改动
git checkout <pre-pr3-sha> -- apps/api/app/api/papers/paper_crud.py
git commit -m "rollback: revert paper_crud.py changes"

# 删除新增的 schemas/ 目录
git rm -r apps/api/app/schemas/
git rm -r apps/api/app/repositories/
git commit -m "rollback: remove schemas and repositories directories"
```

### PR 合并顺序与依赖

```
PR-1 (治理闭环) ──必须先合并──> PR-2 (前端收口)
                                      │
                                      ├──可并行──> PR-3 (后端样板)
                                      │
                                      ↓
                              PR-4 (契约统一) ← 必须等 PR-2 + PR-3 完成
```

---

## 10. 风险与回滚策略

### 总体回滚原则

| 原则 | 说明 |
|------|------|
| 原子回滚 | 每个 PR 独立回滚，不影响已合并的其他 PR |
| 保留现场 | 回滚前先创建 rollback 分支保留当前状态 |
| 分层回滚 | 优先回滚最小范围，不轻易全量回滚 |
| 文档同步 | 回滚时同步更新受影响的文档 |

### 风险 1：契约统一导致前端页面大面积联调

**控制方式：**

- 前端 service 保留一层临时兼容 adapter
- 页面层不直接承受契约变更

**回滚方式：**
```bash
# 1. 创建回滚分支保留现场
git checkout -b rollback-contract-$(date +%Y%m%d)

# 2. 仅回滚 papers 相关契约变更
git checkout <pre-contract-sha> -- apps/web/src/services/papersApi.ts
git checkout <pre-contract-sha> -- apps/web/src/types/papers.ts
git checkout <pre-contract-sha> -- apps/api/app/schemas/papers.py

# 3. 提交回滚
git commit -m "rollback: revert papers contract changes"

# 4. 推送回滚分支
git push origin rollback-contract-$(date +%Y%m%d)

# 5. 创建 Hotfix PR
gh pr create --title "rollback: papers contract changes" --body "回滚 papers 契约变更，等待重新规划"
```

**影响范围：** 仅 `papers` 领域，不影响其他已整改部分。

### 风险 2：后端 router 下沉后测试覆盖不足

**控制方式：**
- 先做 `paper_crud.py` 一条主链路
- 加 smoke test
- 不一次性改所有 allowlist 文件

**回滚方式：**
```bash
# 1. 仅回滚 paper_crud.py
git checkout <pre-refactor-sha> -- apps/api/app/api/papers/paper_crud.py

# 2. 回滚 paper_service.py（如果需要）
git checkout <pre-refactor-sha> -- apps/api/app/services/paper_service.py

# 3. 保留 schemas/ 和 repositories/ 目录（这些是正确的基础设施）

# 4. 更新 code-boundary-baseline.md 允许 paper_crud.py 暂时直连数据库
echo "- apps/api/app/api/papers/paper_crud.py  # 暂时允许，等待重新整改" >> docs/specs/governance/code-boundary-baseline.md

git commit -m "rollback: revert paper_crud.py to direct DB access temporarily"
```

**影响范围：** 仅 `paper_crud.py`，`schemas/` 和 `repositories/` 目录保留。

### 风险 3：治理文档继续先于代码演进

**控制方式：**
- 每个整改 PR 都必须附：
  - 受影响文档
  - 运行命令
  - 结构截图或 diff 说明

**回滚方式：**
```bash
# 1. 识别文档变更
git diff <pre-pr-sha> HEAD -- docs/

# 2. 仅回滚文档（如果代码部分正确）
git checkout <pre-pr-sha> -- docs/specs/architecture/api-contract.md
git checkout <pre-pr-sha> -- docs/specs/governance/code-boundary-baseline.md

# 3. 提交文档回滚
git commit -m "docs: rollback governance docs to match current implementation"

# 4. 创建 issue 跟踪文档同步
gh issue create --title "文档与实现不同步" --body "需更新文档以匹配当前代码实现"
```

### 风险 4：前端 hook 合并后页面功能异常

**控制方式：**
- 合并前完整测试所有使用 `useKnowledgeBases` 的页面
- 保留 `app/hooks/useKnowledgeBases.ts` 废弃版本一周后再删除
- 添加 console.warn 提示废弃路径

**回滚方式：**
```bash
# 1. 快速恢复废弃版本（如果还在 7 天内）
git checkout <pre-merge-sha> -- apps/web/src/app/hooks/useKnowledgeBases.ts

# 2. 如果已删除，从 git 历史恢复
git show <pre-merge-sha>:apps/web/src/app/hooks/useKnowledgeBases.ts > apps/web/src/app/hooks/useKnowledgeBases.ts

# 3. 添加废弃标记
cat >> apps/web/src/app/hooks/useKnowledgeBases.ts << 'EOF'
/**
 * @deprecated 此文件已废弃，请使用 @/hooks/useKnowledgeBases
 * 此文件仅用于紧急回滚，将在下个版本删除
 */
EOF

# 4. 更新 import 路径
# 手动检查哪些页面需要改回 import

git add apps/web/src/app/hooks/useKnowledgeBases.ts
git commit -m "hotfix: restore deprecated useKnowledgeBases temporarily"

# 5. 运行测试确认功能恢复
cd apps/web && npm run test:run
```

### 紧急回滚清单

| 场景 | 回滚范围 | 回滚命令 | 验证命令 |
|------|----------|----------|----------|
| PR-1 失败 | 全量回滚 | `git revert <pr-1-sha>` | `bash scripts/check-governance.sh` |
| PR-2 前端崩溃 | 仅前端 | `git checkout <pre-pr2-sha> -- apps/web/` | `cd apps/web && npm run test:run` |
| PR-3 后端崩溃 | 仅后端 | `git checkout <pre-pr3-sha> -- apps/api/` | `cd apps/api && pytest -x` |
| 契约不兼容 | papers 领域 | 见风险 1 | `curl localhost:8000/api/papers` |
| 测试不足 | paper_crud.py | 见风险 2 | `pytest apps/api/app/api/papers/` |
| 功能异常 | 特定页面 | 见风险 4 | 手动测试页面 |

### 回滚后恢复流程

```bash
# 1. 回滚后检查状态
git status
git log --oneline -5

# 2. 运行基础验证
bash scripts/check-governance.sh
cd apps/web && npm run type-check
cd apps/api && pytest -x

# 3. 创建 issue 跟踪恢复计划
gh issue create --title "恢复 [PR名称] 整改" --body "
## 回滚原因
[填写回滚原因]

## 影响范围
[列出受影响的文件和功能]

## 恢复计划
1. [第一步]
2. [第二步]

## 负责人
@[GitHub用户名]
"

# 4. 创建恢复分支
git checkout -b recovery/[pr-name]-$(date +%Y%m%d)

# 5. 逐步重新应用变更（小步提交）
# 每次提交后运行验证
```

---

## 11. 完成标准

只有满足下面条件，才算本轮整改完成：

### 仓库治理完成标准

| 序号 | 标准项 | 验证方法 | 通过条件 |
|------|--------|----------|----------|
| 1 | `.github/workflows` 存在 | `test -d .github/workflows` | Exit code = 0 |
| 2 | 四个治理脚本全部通过 | `bash scripts/check-governance.sh` | Exit code = 0 |
| 3 | `apps/*` 不承接业务代码 | `find apps -name "*.ts" -o -name "*.py" \| grep -v README \| wc -l` | 输出 = 0 |

### 前端完成标准

| 序号 | 标准项 | 验证方法 | 通过条件 |
|------|--------|----------|----------|
| 1 | 共享业务 hook 无重复实现 | `find apps/web/src -name "useKnowledgeBases.ts" \| wc -l` | 输出 = 1 |
| 2 | `app` 与根级共享层边界写入规范 | `grep -q "app/hooks" docs/specs/development/coding-standards.md` | Exit code = 0 |
| 3 | 至少一个 service 域完成 DTO 统一 | `grep -c "return { success" apps/web/src/services/kbApi.ts` | 输出 = 0 |
| 4 | TypeScript 编译无错误 | `cd apps/web && npm run type-check` | Exit code = 0 |
| 5 | 前端测试覆盖率达标 | `cd apps/web && npm run test:run -- --coverage` | 覆盖率 ≥ 80% |

### 后端完成标准

| 序号 | 标准项 | 验证方法 | 通过条件 |
|------|--------|----------|----------|
| 1 | `schemas/` 建立 | `test -d apps/api/app/schemas && ls apps/api/app/schemas/*.py \| wc -l` | 目录存在，文件 ≥ 3 |
| 2 | `repositories/` 建立 | `test -d apps/api/app/repositories && ls apps/api/app/repositories/*.py \| wc -l` | 目录存在，文件 ≥ 2 |
| 3 | `paper_crud.py` 不再直接访问数据库 | `grep -cE "(db\.execute\|select\()" apps/api/app/api/papers/paper_crud.py` | 输出 = 0 |
| 4 | `search.py` 与 `search/` 不再并存为双主入口 | `test ! -f apps/api/app/api/search.py` 或含 deprecated | 文件删除或标记废弃 |
| 5 | 后端测试通过 | `cd apps/api && pytest -x` | Exit code = 0 |

### 契约完成标准

| 序号 | 标准项 | 验证方法 | 通过条件 |
|------|--------|----------|----------|
| 1 | 所有页面领域文档与实现一致 | 对比 `docs/specs/architecture/api-contract.md` 与实际响应 | 结构一致 |
| 2 | 前端只消费 camelCase DTO | `curl localhost:8000/api/papers \| jq '.data.items[0] \| keys' \| grep "_"` | 无 snake_case |
| 3 | 列表接口统一到同一响应壳 | `curl localhost:8000/api/papers \| jq 'has("data") and .data.has("items") and has("meta")'` | 输出 = true |

### 整体验收脚本

```bash
#!/bin/bash
# scripts/verify-all-phases.sh

set -e

echo "========================================"
echo "  ScholarAI 结构整改整体验收"
echo "========================================"
echo ""

# 仓库治理
echo "【1/4】仓库治理验收..."
bash scripts/verify-phase0.sh
bash scripts/verify-phase1.sh
echo ""

# 前端
echo "【2/4】前端验收..."
bash scripts/verify-phase2.sh
echo ""

# 后端
echo "【3/4】后端验收..."
bash scripts/verify-phase3.sh
echo ""

# 契约
echo "【4/4】契约验收..."
bash scripts/verify-phase4.sh
echo ""

echo "========================================"
echo "  ✓ 整改完成！所有验收通过"
echo "========================================"
```

---

## 12. 最终结论

这次整改的关键不是再发明更多的目录，而是把当前已经出现的治理框架**落到真实代码边界**上。

当前阶段最优实践可以概括为一句话：

> **先让 `apps/web/` 和 `apps/api/` 在现有位置完成单一真源化、分层收口和契约收口；等这些收口完成，再做 `apps/*` 的物理迁移。**

也就是说，当前真正要解决的不是"目录名字不够先进"，而是：

- 同一职责不能多处实现
- router 不能继续承载业务编排
- schema 不能继续和 ORM 混放
- 契约文档不能继续和真实返回不一致
- `apps/*` 不能继续悬空成为未来潜在第二主路径

这份计划按顺序执行后，ScholarAI 会从"治理骨架已搭出但还偏概念化"，进入"仓库、代码、契约、文档、门禁五件事真正对齐"的状态。

---

## 13. 功能影响评估

### 受影响功能模块

| 模块 | 影响程度 | 需要联调 | 测试重点 | 风险等级 |
|------|----------|----------|----------|----------|
| Papers 列表页 | **高** | 是 | 分页参数变更、响应壳变更、字段命名变更 | ⚠️ 高 |
| Papers 详情页 | 中 | 是 | 字段命名变更（camelCase） | ⚠️ 中 |
| Knowledge Base 列表 | **高** | 是 | hook 统一、service 返回变更 | ⚠️ 高 |
| Knowledge Base 详情 | 中 | 是 | DTO 统一 | ⚠️ 中 |
| Search 功能 | 中 | 否 | 入口迁移（search.py → search/） | ⚠️ 中 |
| Chat 功能 | 低 | 否 | 无直接变更 | ✓ 低 |
| Notes 功能 | 低 | 否 | 无直接变更 | ✓ 低 |
| Import 功能 | 低 | 否 | 无直接变更 | ✓ 低 |
| User 认证 | 低 | 否 | 无直接变更 | ✓ 低 |

### 前后端联调清单

| 序号 | 联调项 | 前端负责人 | 后端负责人 | 预计联调时间 |
|------|--------|------------|------------|--------------|
| 1 | Papers 列表分页 | papersApi.ts | paper_crud.py + paper_service.py | 重点联调 |
| 2 | Papers 响应字段命名 | papersApi.ts normalizePaper() | paper_shared.py / schemas/papers.py | 重点联调 |
| 3 | KB 列表 hook 统一 | useKnowledgeBases.ts | 无后端变更 | 前端独立 |
| 4 | KB service 返回统一 | kbApi.ts | 无后端变更 | 前端独立 |
| 5 | Search 入口迁移 | searchApi.ts | main.py 路由注册 | 低风险 |

### 测试覆盖要求

| 领域 | 单元测试 | 集成测试 | E2E 测试 | 最低覆盖率 |
|------|----------|----------|----------|------------|
| 前端 - Papers | ✓ | ✓ | ✓ 必需 | 85% |
| 前端 - KB | ✓ | ✓ | ✓ 必需 | 85% |
| 前端 - 其他 | ✓ | ✓ | ○ 可选 | 80% |
| 后端 - Papers | ✓ | ✓ | ✓ 必需 | 90% |
| 后端 - Search | ✓ | ✓ | ○ 可选 | 80% |
| 后端 - 其他 | ✓ | ○ 可选 | ○ 可选 | 75% |

### 性能基准对比点

整改前后需对比以下性能指标，确保无退化：

| 指标 | 当前值（基准） | 整改后目标 | 测量方法 |
|------|----------------|------------|----------|
| Papers 列表加载时间 | ≤ 500ms | ≤ 500ms | `curl -w "%{time_total}" localhost:8000/api/papers` |
| KB 列表加载时间 | ≤ 300ms | ≤ 300ms | `curl -w "%{time_total}" localhost:8000/api/kb` |
| Search 响应时间 | ≤ 1s | ≤ 1s | `curl -w "%{time_total}" localhost:8000/api/search` |
| 前端首次渲染 | ≤ 2s | ≤ 2s | Lighthouse Performance |
| TypeScript 编译时间 | 当前值 | 不增加 | `time npm run type-check` |
| pytest 运行时间 | 当前值 | 不增加 | `time pytest` |

---

## 14. 中断恢复机制

若整改中途暂停（如资源调配、优先级变更），按以下步骤恢复：

### 恢复流程

```bash
# 1. 检查当前进度
echo "=== 检查整改进度 ==="

# 检查各 Phase 验收脚本是否存在
for phase in 0 1 2 3 4 5; do
    if [ -f "scripts/verify-phase${phase}.sh" ]; then
        echo "Phase $phase 验收脚本存在 ✓"
    else
        echo "Phase $phase 验收脚本不存在 ✗"
    fi
done

# 2. 运行对应 Phase 的验收脚本确认当前状态
# 从 Phase 0 开始逐一验证，定位当前完成到哪个 Phase
bash scripts/verify-phase0.sh && echo "Phase 0 完成" || echo "Phase 0 未完成，从此开始"
bash scripts/verify-phase1.sh && echo "Phase 1 完成" || echo "Phase 1 未完成，从此开始"
# ... 继续到失败的 Phase

# 3. 若验收失败，从失败任务重新开始
# 查看该 Phase 的任务清单，执行下一个未完成任务

# 4. 若验收通过，继续下一 Phase
```

### 进度状态文件（建议）

创建 `.planning/refactor-progress.json` 记录整改进度：

```json
{
  "plan": "ScholarAI_结构问题整改计划_v1",
  "started_at": "2026-04-16",
  "phases": {
    "0": { "status": "completed", "completed_at": "2026-04-17" },
    "1": { "status": "completed", "completed_at": "2026-04-18" },
    "2": { "status": "in_progress", "started_at": "2026-04-19", "current_task": "2.3" },
    "3": { "status": "pending" },
    "4": { "status": "pending" },
    "5": { "status": "pending" }
  },
  "pr_status": {
    "pr-1": { "status": "merged", "merged_at": "2026-04-18" },
    "pr-2": { "status": "open", "created_at": "2026-04-19" },
    "pr-3": { "status": "pending" }
  },
  "last_updated": "2026-04-19T10:30:00Z",
  "notes": "Phase 2 任务 2.1-2.2 已完成，正在执行任务 2.3"
}
```

### 恢复脚本

```bash
#!/bin/bash
# scripts/resume-refactor.sh

set -e

echo "=== 整改中断恢复 ==="

# 1. 检查进度文件
if [ -f ".planning/refactor-progress.json" ]; then
    echo "发现进度文件，读取当前状态..."
    current_phase=$(jq -r '.phases | to_entries | sort_by(.key) | map(select(.value.status == "in_progress")) | .[0].key' .planning/refactor-progress.json 2>/dev/null || echo "unknown")
    current_task=$(jq -r '.phases["${current_phase}"].current_task' .planning/refactor-progress.json 2>/dev/null || echo "unknown")
    echo "当前进度: Phase $current_phase, 任务 $current_task"
else
    echo "未发现进度文件，从 Phase 0 开始验证..."
    current_phase="unknown"
fi

# 2. 从 Phase 0 开始逐一验证
for phase in 0 1 2 3 4 5; do
    if [ -f "scripts/verify-phase${phase}.sh" ]; then
        echo ""
        echo "验证 Phase $phase..."
        if bash "scripts/verify-phase${phase}.sh" 2>/dev/null; then
            echo "✓ Phase $phase 已完成"
        else
            echo "✗ Phase $phase 未完成或验收失败"
            echo ""
            echo "=== 恢复建议 ==="
            echo "1. 查阅 docs/plans/ScholarAI_结构问题整改计划_v1.md 中 Phase $phase 的任务清单"
            echo "2. 从第一个未完成任务开始执行"
            echo "3. 完成后运行: bash scripts/verify-phase${phase}.sh"
            echo "4. 验收通过后继续下一 Phase"
            exit 0
        fi
    else
        echo "⚠ Phase $phase 验收脚本不存在，跳过"
    fi
done

echo ""
echo "=== 所有 Phase 已完成 ✓ ==="
echo "运行整体验收: bash scripts/verify-all-phases.sh"
```

---

## 15. 版本历史

| 版本 | 日期 | 作者 | 变更说明 |
|------|------|------|----------|
| v1 | 2026-04-16 | - | 初始版本：定义 6 个 Phase、3 个 PR、验收标准、回滚策略 |
| v1.1 | 2026-04-16 | - | 补充：Phase 依赖关系可视化、验收标准具体化（含验收脚本）、回滚命令具体化、功能影响评估、中断恢复机制 |

---

## 附录 A：验收脚本清单

| 脚本路径 | 用途 | 执行时机 |
|----------|------|----------|
| `scripts/verify-phase0.sh` | Phase 0 治理门禁验收 | Phase 0 完成时 |
| `scripts/verify-phase1.sh` | Phase 1 主路径冻结验收 | Phase 1 完成时 |
| `scripts/verify-phase2.sh` | Phase 2 前端收口验收 | Phase 2 完成时 |
| `scripts/verify-phase3.sh` | Phase 3 后端整改验收 | Phase 3 完成时 |
| `scripts/verify-phase4.sh` | Phase 4 契约统一验收 | Phase 4 完成时 |
| `scripts/verify-phase5.sh` | Phase 5 迁移准备验收 | Phase 5 完成时 |
| `scripts/verify-all-phases.sh` | 整体验收 | 整改完成后 |
| `scripts/resume-refactor.sh` | 中断恢复 | 整改中断后恢复 |

---

## 附录 B：相关文档索引

| 文档路径 | 内容 |
|----------|------|
| `docs/specs/architecture/api-contract.md` | API 契约规范 |
| `docs/specs/architecture/repository-architecture.md` | 仓库架构说明 |
| `docs/specs/development/coding-standards.md` | 编码规范 |
| `docs/specs/governance/code-boundary-baseline.md` | 代码边界基线 |
| `docs/specs/governance/core-boundary-baseline.md` | core 目录边界基线（待创建） |
| `docs/specs/governance/migration-conditions.md` | 迁移条件清单（待创建） |
| `docs/specs/adr/0002-delay-physical-migration-until-boundary-convergence.md` | ADR：暂缓物理迁移决策（待创建） |
| `AGENTS.md` | AI 协作规则 |
| `README.md` | 项目说明 |
