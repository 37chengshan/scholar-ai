---
owner: platform
status: done
depends_on: []
last_verified_at: 2026-04-17
evidence_commits:
  - historical-pr3-commit-to-backfill
---

# PR3 执行方案：物理迁移到 `apps/*`

## 1. 文档目的

本文件用于指导 **PR3** 在一个 PR 内一次性完成以下整改：

1. 将前端真实代码主路径从 `frontend/` 迁移到 `apps/web/`
2. 将后端真实代码主路径从 `backend-python/` 迁移到 `apps/api/`
3. 将仓库治理、验收脚本、CI、文档、开发命令与测试入口统一切换到新路径
4. 将仓库从“逻辑映射阶段”切换到“物理主路径阶段”

> 本 PR3 只做 **物理迁移 + 路径真源切换**，不夹带业务功能重构。

---

## 2. 当前基线

在 PR3 开始前，仓库当前状态是：

- `README.md` 明确说明当前阶段**唯一真实代码主路径**仍是 `frontend` 与 `backend-python`，`apps/web -> frontend`、`apps/api -> backend-python` 只是逻辑映射。
- `AGENTS.md` 仍要求前端代码只能落在 `frontend`，后端代码只能落在 `backend-python`，`apps/web` 与 `apps/api` 不允许承接业务源码。
- `docs/governance/migration-conditions.md` 已定义：只有在 Phase 0~5 验收全部通过后，才允许进入物理迁移执行阶段。
- `pnpm-workspace.yaml` 已提前包含 `frontend` 与 `apps/*`，说明工作区底座已准备好。
- `scripts/check-structure-boundaries.sh` 当前仍要求 `frontend` 与 `backend-python` 必须存在，并阻止 `apps/web` / `apps/api` 承接真实业务代码。
- `scripts/check-code-boundaries.sh` 当前仍以 `frontend/src/...` 与 `backend-python/app/...` 为检查目标。

因此，PR3 的关键工作不是继续补治理，而是 **整体翻转现有规则**。

---

## 3. PR3 范围与边界

### 3.1 本 PR 必须完成

- `frontend/` → `apps/web/`
- `backend-python/` → `apps/api/`
- 所有文档、脚本、CI、命令、测试入口同步改到新路径
- 所有治理规则从“apps 不承接源码”切换为“apps 是唯一真实代码主路径”

### 3.2 本 PR 不做

- KB / Chat 交互优化
- RAG 检索逻辑升级
- 新接口设计
- service / repository 新一轮重构
- `packages/*` 承接真实业务代码

### 3.3 迁移原则

1. **只做物理迁移，不混业务重构**
2. **必须使用 `git mv` 保留历史**
3. **一次性切换真源，不保留双实现路径**
4. **旧路径允许删除，或仅保留迁移说明；不得继续承接真实代码**

---

## 4. 依赖关系

### 4.1 依赖图

```text
A. 基线锁定与备份
  ↓
B. 清理 apps 占位 README（为 git mv 腾位置）
  ↓
C. 前端迁移到 apps/web
  ↓
D. 前端相关脚本/CI/文档改路径
  ↓
E. 后端迁移到 apps/api
  ↓
F. 后端相关脚本/CI/文档改路径
  ↓
G. 治理脚本与验收脚本翻转规则
  ↓
H. 清理 legacy 路径残留引用
  ↓
I. 全量验收
  ↓
J. 提交 PR3
```

### 4.2 关键依赖说明

- **B 必须在 C/E 之前完成**：`apps/web`、`apps/api` 现在是占位目录，必须先移除占位 README。
- **D 必须紧跟 C**：否则前端 type-check / test / CI 会立即断。
- **F 必须紧跟 E**：否则 pytest、Docker、启动脚本会断。
- **G 必须在 C~F 之后执行**：因为现有治理脚本还在禁止 `apps/*` 承接源码。
- **I 必须最后执行**：验收脚本本身也要先改到新路径。

---

## 5. 逐文件修改清单

> 说明：本清单分为“目录级迁移”“必须修改”“按命中修改”三类。

### 5.1 目录级迁移（必须使用 `git mv`）

#### 前端
- `frontend/` → `apps/web/`

#### 后端
- `backend-python/` → `apps/api/`

#### 占位目录处理
先删除：
- `apps/web/README.md`
- `apps/api/README.md`

然后再执行目录迁移。

---

### 5.2 仓库真源与规则文件（必须修改）

#### 根级文件
- `README.md`
- `AGENTS.md`
- `architecture.md`
- `pnpm-workspace.yaml`

#### docs
- `docs/architecture/system-overview.md`
- `docs/architecture/api-contract.md`
- `docs/domain/resources.md`
- `docs/development/coding-standards.md`
- `docs/development/pr-process.md`
- `docs/development/testing-strategy.md`
- `docs/governance/code-boundary-baseline.md`
- `docs/governance/migration-conditions.md`

#### packages 说明文件
- `packages/types/README.md`
- `packages/sdk/README.md`
- `packages/ui/README.md`
- `packages/config/README.md`

这些文件都必须把：
- `frontend`
- `backend-python`
- `apps/web -> frontend`
- `apps/api -> backend-python`

改成：
- `apps/web`
- `apps/api`
- `apps/web` / `apps/api` 为唯一真实代码主路径

---

### 5.3 CI / Workflow / 部署（必须修改）

#### GitHub Actions
- `.github/workflows/governance-baseline.yml`
- `.github/workflows/test.yml`
- 其他 workflow 中所有 `frontend` / `backend-python` 工作目录与路径

#### 根级任务/构建文件（按存在修改）
- `package.json`
- `Makefile`
- `turbo.json`
- `nx.json`
- `justfile`

#### 部署 / 容器 / infra（按存在修改）
- `docker-compose.yml`
- `deploy-cloud.sh`
- `deploy-cloud-fixed.sh`
- `infra/**` 中所有引用旧路径的文件
- Dockerfile / build context 相关文件

---

### 5.4 治理脚本（必须修改）

- `scripts/check-doc-governance.sh`
- `scripts/check-structure-boundaries.sh`
- `scripts/check-code-boundaries.sh`
- `scripts/check-governance.sh`

#### 重点变化

##### `scripts/check-structure-boundaries.sh`
当前行为：
- 要求 `frontend`、`backend-python` 必须存在
- 禁止 `apps/web` / `apps/api` 出现真实业务代码

整改后：
- `frontend`、`backend-python` 不再是 required dirs
- `apps/web`、`apps/api` 必须存在真实代码
- `apps/web/src` 必须存在
- `apps/api/app` 必须存在
- 若 `frontend`、`backend-python` 仍存在业务代码，应视为违规

##### `scripts/check-code-boundaries.sh`
当前扫描目录：
- `frontend/src/app/pages`
- `frontend/src/app/components`
- `frontend/src/hooks`
- `frontend/src/app/hooks`
- `backend-python/app/api`

整改后改为：
- `apps/web/src/app/pages`
- `apps/web/src/app/components`
- `apps/web/src/hooks`
- `apps/web/src/app/hooks`
- `apps/api/app/api`

---

### 5.5 验收脚本（必须修改）

- `scripts/verify-phase0.sh`
- `scripts/verify-phase1.sh`
- `scripts/verify-phase2.sh`
- `scripts/verify-phase3.sh`
- `scripts/verify-phase4.sh`
- `scripts/verify-phase5.sh`
- `scripts/verify-all-phases.sh`
- `scripts/resume-refactor.sh`

#### 必改规则
- 所有 `cd frontend` → `cd apps/web`
- 所有 `cd backend-python` → `cd apps/api`
- 所有 `frontend/src/...` → `apps/web/src/...`
- 所有 `backend-python/app/...` → `apps/api/app/...`
- Phase 5 从“迁移准备验收”改成“迁移完成验收”

---

### 5.6 业务代码目录迁移（移动为主，不改业务逻辑）

#### 前端整目录迁移
- `frontend/src/**` → `apps/web/src/**`
- `frontend/package.json`
- `frontend/tsconfig*.json`
- `frontend/vite.config.*`
- `frontend/vitest.config.*`
- `frontend/.env*`
- `frontend/public/**`
- `frontend/e2e/**`（如果存在）

#### 后端整目录迁移
- `backend-python/app/**` → `apps/api/app/**`
- `backend-python/tests/**` → `apps/api/tests/**`
- `backend-python/requirements.txt`
- `backend-python/pyproject.toml`
- `backend-python/alembic.ini`
- `backend-python/.env*`

---

### 5.7 路径敏感文件（必须 grep 命中清理）

第一轮扫描：

```bash
rg -n "frontend|backend-python" \
README.md AGENTS.md architecture.md \
docs scripts .github packages \
pnpm-workspace.yaml docker-compose.yml \
deploy-cloud.sh deploy-cloud-fixed.sh Makefile package.json
```

第二轮扫描：

```bash
rg -n "frontend|backend-python" . \
--glob '!docs/plans/**' \
--glob '!docs/adr/**' \
--glob '!node_modules/**'
```

处理规则：
- `docs/plans/**`、`docs/adr/**` 可保留历史路径说明
- 其他位置全部改为新路径，或删除旧引用

---

## 6. 执行步骤

### Step 0：拉取主线并锁定基线

```bash
git checkout main
git pull origin main
bash scripts/verify-all-phases.sh
bash scripts/check-governance.sh
```

### Step 1：创建工作分支与回滚锚点

```bash
git switch -c chore/pr3-physical-migrate-to-apps
git branch backup/pre-pr3-physical-migration
git tag pre-pr3-physical-migration
git push origin main:backup/pre-pr3-physical-migration
```

### Step 2：移除占位 README，腾出 `apps` 目录

```bash
git rm apps/web/README.md
git rm apps/api/README.md
rmdir apps/web apps/api
```

### Step 3：迁移前端到 `apps/web`

```bash
git mv frontend apps/web
```

### Step 4：先修前端相关路径

必须完成以下内容：
- `README.md`、`AGENTS.md` 中的前端路径
- workflow / CI 中的前端工作目录
- `pnpm-workspace.yaml`
- `scripts/check-code-boundaries.sh`
- `scripts/verify-phase2.sh`
- 所有 `cd frontend` 命令

### Step 5：前端局部验证

```bash
cd apps/web && npm install
cd apps/web && npm run type-check
cd apps/web && npm run test:run
cd ../..
```

### Step 6：迁移后端到 `apps/api`

```bash
git mv backend-python apps/api
```

### Step 7：修后端相关路径

必须完成以下内容：
- `README.md`、`AGENTS.md` 中的后端路径
- workflow / CI 中的后端工作目录
- `scripts/check-code-boundaries.sh`
- `scripts/check-structure-boundaries.sh`
- `scripts/verify-phase3.sh`
- 所有 `cd backend-python` 命令

### Step 8：翻转治理与文档规则

重点改：
- `README.md`
- `AGENTS.md`
- `docs/governance/migration-conditions.md`
- `docs/governance/code-boundary-baseline.md`
- `packages/*/README.md`
- 所有 verify 脚本
- 所有 check 脚本

### Step 9：清理 legacy 引用

```bash
rg -n "frontend|backend-python" \
README.md AGENTS.md architecture.md docs scripts .github packages \
pnpm-workspace.yaml docker-compose.yml deploy-cloud.sh deploy-cloud-fixed.sh Makefile package.json \
--glob '!docs/plans/**' --glob '!docs/adr/**'
```

### Step 10：全量验收

执行第 8 章中的全部验收命令。

### Step 11：提交并推 PR3

建议至少拆成 5 个 commit：

1. `chore: remove apps placeholder readmes and prepare physical migration`
2. `chore: move frontend to apps/web`
3. `chore: move backend-python to apps/api`
4. `chore: flip governance and docs to physical apps paths`
5. `test: update validation scripts and path-sensitive checks`

---

## 7. 验收清单

### 7.1 结构验收

- `apps/web/src` 存在
- `apps/api/app` 存在
- `frontend` 不再承接业务代码
- `backend-python` 不再承接业务代码
- `apps/web` / `apps/api` 成为唯一真实代码主路径

### 7.2 文档验收

- `README.md` 已改成物理主路径叙述
- `AGENTS.md` 已翻转规则
- `migration-conditions.md` 已从“迁移前置条件”改为“迁移完成状态”
- `packages/*/README.md` 已统一到 `apps/web` / `apps/api`

### 7.3 CI / 脚本验收

- `governance-baseline.yml` 通过
- `test.yml` 通过
- `verify-phase0~5.sh` 通过
- `verify-all-phases.sh` 通过
- `check-doc-governance.sh` 通过
- `check-structure-boundaries.sh` 通过
- `check-code-boundaries.sh` 通过
- `check-governance.sh` 通过

### 7.4 前端验收

- `apps/web` 下 `type-check` 通过
- `apps/web` 下 `test:run` 通过
- 路径敏感测试（如 `KnowledgeBaseDetail.test.tsx`）保持通过

### 7.5 后端验收

- `apps/api` 下 `pytest -x --tb=short` 通过
- `tests/unit/test_services.py` 通过
- `tests/unit/test_unified_search.py` 通过

### 7.6 残留引用验收

- 非历史文档中不再出现 `frontend` / `backend-python` 作为主路径

---

## 8. 验收命令

### 8.1 结构与 legacy 检查

```bash
test -d apps/web/src
test -d apps/api/app
test ! -d frontend
test ! -d backend-python
```

如果保留 legacy 空目录，则改为：

```bash
find frontend -type f \( -name "*.ts" -o -name "*.tsx" -o -name "*.py" \) | wc -l
find backend-python -type f \( -name "*.ts" -o -name "*.tsx" -o -name "*.py" \) | wc -l
```

结果必须都为 `0`。

### 8.2 残留引用 grep

```bash
rg -n "frontend|backend-python" \
README.md AGENTS.md architecture.md docs scripts .github packages \
pnpm-workspace.yaml docker-compose.yml deploy-cloud.sh deploy-cloud-fixed.sh Makefile package.json \
--glob '!docs/plans/**' --glob '!docs/adr/**'
```

### 8.3 治理脚本

```bash
bash scripts/check-doc-governance.sh
bash scripts/check-structure-boundaries.sh
bash scripts/check-code-boundaries.sh
bash scripts/check-governance.sh
```

### 8.4 分阶段验收

```bash
bash scripts/verify-phase0.sh
bash scripts/verify-phase1.sh
bash scripts/verify-phase2.sh
bash scripts/verify-phase3.sh
bash scripts/verify-phase4.sh
bash scripts/verify-phase5.sh
bash scripts/verify-all-phases.sh
```

### 8.5 前端验收

```bash
cd apps/web && npm install
cd apps/web && npm run type-check
cd apps/web && npm run test:run
cd ../..
```

### 8.6 后端验收

```bash
cd apps/api && pytest -x --tb=short
cd apps/api && pytest -q tests/unit/test_services.py --maxfail=1
cd apps/api && pytest -q tests/unit/test_unified_search.py --maxfail=1
cd ../..
```

### 8.7 本地总检查

```bash
bash scripts/check-governance.sh && \
bash scripts/verify-all-phases.sh && \
(cd apps/web && npm run type-check && npm run test:run) && \
(cd apps/api && pytest -q tests/unit/test_services.py --maxfail=1 && pytest -q tests/unit/test_unified_search.py --maxfail=1)
```

---

## 9. 回滚方案

### 9.1 PR 未合并时放弃分支

```bash
git switch main
git branch -D chore/pr3-physical-migrate-to-apps
git tag -d pre-pr3-physical-migration
```

若本地未提交但改乱：

```bash
git reset --hard
git clean -fd
```

### 9.2 PR 已合并后的回滚

先找 merge commit：

```bash
git log --oneline --merges --grep="physical migrate"
```

然后：

```bash
git checkout -b revert/pr3-physical-migration
git revert -m 1 <merge_commit_sha>
git push origin revert/pr3-physical-migration
```

### 9.3 紧急恢复到迁移前快照

```bash
git reset --hard pre-pr3-physical-migration
```

### 9.4 最稳妥的保险做法

在开始前保留远端备份分支：

```bash
git push origin main:backup/pre-pr3-physical-migration
```

---

## 10. Definition of Done

PR3 视为完成，必须同时满足：

1. `apps/web` 与 `apps/api` 成为唯一真实代码主路径
2. 所有开发/测试/部署命令都切换到新路径
3. 所有治理脚本与验收脚本全绿
4. 所有核心文档已翻转到物理主路径叙述
5. 非历史文档中不再保留旧主路径引用
6. PR 不包含额外业务逻辑重构

---

## 11. 执行提醒

- 这是一个 **路径真源切换 PR**，不是功能 PR。
- 不要把 KB/Chat 修复、RAG 优化、API 协议调整混进来。
- 建议先迁前端再迁后端，但最终在同一个 PR 内合并完成。
- 任何一个阶段发现大面积测试崩溃，应先停止继续迁移，优先修复路径与脚本，再继续下一步。

