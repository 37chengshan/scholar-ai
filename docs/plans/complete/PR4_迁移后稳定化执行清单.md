---
owner: platform
status: done
depends_on:
  - PR3
last_verified_at: 2026-04-17
evidence_commits:
  - historical-pr4-commit-to-backfill
---

# PR-4 迁移后稳定化执行清单（基于当前代码现状）

## 1. 目标

PR-4 不是继续做大规模业务重构，而是把 **PR-3 物理迁移后的仓库收口到“稳定可持续开发”状态**。

本 PR 的目标分成四层：

1. **清理迁移残留**：删除被错误提交到仓库的运行时产物、覆盖率目录、虚拟环境、嵌套旧仓库副本、日志与临时文件。
2. **封死 legacy 回流**：让治理脚本、CI、文档、忽略规则同时阻止旧路径、运行时产物、嵌套仓库再次进入主线。
3. **收紧仓库边界**：把 `apps/web`、`apps/api` 之外的“非真源目录”进一步压缩；让 `packages/*` 继续保持边界清晰。
4. **顺手多做一点低风险内容**：补齐 repo hygiene 脚本、Makefile 验证入口、根级 npm scripts、迁移后稳定期说明文档。

---

## 2. 当前代码现状（来自实际源码包）

### 2.1 已经完成的部分

- 仓库主线已完成物理迁移，README 已明确写明：当前唯一真实代码主路径是 `apps/web` 与 `apps/api`。
- `.github/workflows/governance.yml` 已经在按 `apps/web` 和 `apps/api` 运行前端 type-check 与后端 smoke tests。
- `scripts/check-structure-boundaries.sh` 已经从“逻辑映射阶段”翻转到“物理主路径阶段”，会拒绝 `frontend/`、`backend-python/` 这类 legacy 根级实现路径。
- `scripts/verify-phase0.sh` 到 `scripts/verify-phase5.sh` 已经全部切换到 `apps/web` / `apps/api` 验收。

### 2.2 迁移后仍然存在的问题（源码包中真实存在）

以下内容说明仓库仍处于“可用但不够干净”的状态，适合在 PR-4 一次性收口：

#### A. 根目录仍有明显运行时 / 测试残留

- `logs/`
- `test-results/`
- `uploads/`
- `scholar-ai/`（其中还包含 `scholar-ai/backend-python/...` 旧路径副本）

#### B. `apps/api` 目录仍混入运行时 / 本地环境产物

- `apps/api/venv/`
- `apps/api/htmlcov/`
- `apps/api/htmlcov_reranker/`
- `apps/api/alembic/__pycache__/`
- `apps/api/app/__pycache__/`
- `apps/api/tests/__pycache__/`

#### C. `apps/web` 目录仍混入运行时 / 临时目录

- `apps/web/test-results/`
- `apps/web/frontend.log`
- `apps/web/.github/`（空目录）
- `apps/web/packages/temp-package/...`（空壳目录）

#### D. 文档与脚本仍有少量“迁移后稳定化”缺口

- `.gitignore` 仍保留大量旧路径忽略规则，但没有形成“迁移后 hygiene 最小集”说明。
- `docs/governance/migration-conditions.md` 仍偏“迁移前置条件/迁移准入”视角，缺少“迁移后稳定期”操作说明。
- `scripts/check-governance.sh` 当前只校验文档和基础脚本存在，没有单独校验“tracked runtime artifacts / nested legacy snapshot / local venv 提交”等问题。
- 根级 `package.json`、`Makefile` 还缺少一键执行“迁移后稳定化验证”的命令入口。

---

## 3. PR-4 范围（建议一次性做完）

### 3.1 本 PR 必做

1. 删除已提交的运行时产物、日志、覆盖率、虚拟环境、嵌套旧仓库副本。
2. 新增一个 **repo hygiene 校验脚本**，并接入治理脚本与 CI。
3. 更新 `.gitignore`，把迁移后稳定化需要的忽略规则收口到 `apps/*` 现实路径。
4. 更新 README / AGENTS / migration docs，让仓库协作规则从“迁移完成”推进到“迁移后稳定开发”。
5. 补一键验证入口（Makefile + root package scripts）。

### 3.2 本 PR 允许顺手多做一点（推荐）

1. 新增 `docs/reports/post-migration-stabilization-checklist.md`，作为 PR-4 交付报告模板。
2. 新增 `scripts/clean-repo-artifacts.sh`，用于本地一键清除测试、coverage、venv、日志残留。
3. 在 `scripts/check-structure-boundaries.sh` 中加更严格的“嵌套仓库快照”与“apps 内 runtime artifact”检查。
4. 在 `.github/workflows/governance.yml` 中增加 hygiene check step。

### 3.3 本 PR 不做

1. KB / Chat 页面重构
2. RAG 解析 / 检索逻辑升级
3. `packages/types` / `packages/sdk` 正式承接代码
4. 大规模 service / repository 再拆分
5. 新增功能开发

---

## 4. 执行顺序与依赖顺序

### 4.1 总体顺序

```text
S0 基线复核
  ↓
S1 删除 tracked artifacts / legacy snapshot
  ↓
S2 收紧 .gitignore 与本地清理脚本
  ↓
S3 新增 repo hygiene 检查脚本
  ↓
S4 把 hygiene 检查接入 governance / CI / Makefile / package.json
  ↓
S5 更新 README / AGENTS / migration docs / testing docs
  ↓
S6 全量验收
  ↓
S7 生成 PR-4 交付报告
```

### 4.2 依赖关系说明

- **S1 必须先于 S3/S6**：如果不先删掉已跟踪的运行时产物，新加的 hygiene 检查会立即失败。
- **S2 必须紧跟 S1**：否则这些产物很容易再次被误提交。
- **S3 必须先于 S4**：先有脚本，再接 CI / Makefile / npm scripts。
- **S5 放在 S4 之后**：确保文档描述与实际脚本行为一致。
- **S6 最后执行**：所有规则翻新后再做整体验收。

---

## 5. 交付清单（Definition of Done）

PR-4 完成后，应交付以下内容：

### 5.1 代码与目录层

- 仓库中不再跟踪以下目录/内容：
  - `logs/archive/**`
  - `test-results/**`
  - `uploads/**`
  - `apps/web/test-results/**`
  - `apps/web/frontend.log`
  - `apps/api/venv/**`
  - `apps/api/htmlcov/**`
  - `apps/api/htmlcov_reranker/**`
  - `apps/api/**/__pycache__/**`
  - `scholar-ai/backend-python/**`
- `apps/web` 与 `apps/api` 继续作为唯一真实代码主路径。
- 不再存在嵌套旧仓库快照或 legacy 实现副本。

### 5.2 脚本与 CI 层

- 新增 `scripts/check-runtime-hygiene.sh`
- 新增 `scripts/clean-repo-artifacts.sh`
- `scripts/check-governance.sh` 接入 runtime hygiene 检查
- `.github/workflows/governance.yml` 接入 hygiene check
- 根级 `package.json` 新增 `check:runtime-hygiene`、`verify:post-migration`
- `Makefile` 新增 `verify`、`clean-runtime`

### 5.3 文档层

- `README.md` 新增“迁移后稳定期”说明
- `AGENTS.md` 新增“禁止提交 runtime artifact / nested snapshot”的规则
- `docs/governance/migration-conditions.md` 改为“迁移完成后的稳定化守则 + 退出条件”
- `docs/development/testing-strategy.md` 增加“不要提交测试产物 / coverage / 本地 venv”规则
- 新增 `docs/reports/post-migration-stabilization-checklist.md`

---

## 6. 具体修改文件清单

下面按 **新增 / 修改 / 删除** 分类列出。

---

### 6.1 新增文件

#### A. 新增仓库 hygiene 校验脚本

1. `scripts/check-runtime-hygiene.sh`
   - 检查以下内容不得被跟踪或不得存在：
     - `logs/archive/**`
     - `test-results/**`
     - `apps/web/test-results/**`
     - `apps/web/frontend.log`
     - `apps/api/venv/**`
     - `apps/api/htmlcov/**`
     - `apps/api/htmlcov_reranker/**`
     - `**/__pycache__/**`
     - `scholar-ai/backend-python/**`
   - 检查是否存在嵌套仓库快照目录（如 `scholar-ai/`）
   - 检查 `apps/web/.github` 这类 app 内工作流残留目录

2. `scripts/clean-repo-artifacts.sh`
   - 本地一键删除运行时与测试残留：
     - `logs/archive`
     - `test-results`
     - `apps/web/test-results`
     - `apps/web/frontend.log`
     - `apps/api/htmlcov*`
     - `apps/api/venv`
     - `apps/api/**/__pycache__`
   - 仅清理本地，不负责 Git 删除已跟踪文件

#### B. 新增稳定化报告模板（推荐）

3. `docs/reports/post-migration-stabilization-checklist.md`
   - 记录本次 PR-4 的清理范围
   - 记录本地验证结果
   - 记录 CI 结果
   - 记录残留风险（如不清理的目录）

---

### 6.2 必改文件

#### A. 忽略规则与根级入口

1. `.gitignore`
   - 补齐/强调以下规则：
     - `apps/web/test-results/`
     - `apps/web/*.log`
     - `apps/api/htmlcov/`
     - `apps/api/htmlcov_*/`
     - `apps/api/.coverage`
     - `apps/api/venv/`
     - `apps/api/**/__pycache__/`
     - `scholar-ai/`
   - 删除无意义或误导性的旧路径注释，改成“apps 真实路径”表述

2. `package.json`
   - 新增 scripts：
     - `check:runtime-hygiene`
     - `verify:post-migration`
     - `clean:runtime`

3. `Makefile`
   - 新增 targets：
     - `verify`
     - `clean-runtime`
   - `clean` 目标同步调用 `scripts/clean-repo-artifacts.sh`

#### B. 治理脚本

4. `scripts/check-governance.sh`
   - 在现有文档/边界检查之后新增：
     - `bash scripts/check-runtime-hygiene.sh`

5. `scripts/check-structure-boundaries.sh`
   - 在现有 legacy root path 检查基础上，再加：
     - 根级 `scholar-ai/` 禁止存在
     - `apps/web/.github/` 禁止存在
     - `apps/web/packages/` 禁止存在（若非明确需要）
     - `apps/api/venv/` 禁止存在
     - `apps/api/htmlcov*` 禁止存在
     - `apps/api/**/__pycache__` 禁止存在
     - `apps/web/test-results/` 禁止存在

6. `scripts/verify-phase0.sh`
   - 在治理脚本通过之外，额外确认 `check-runtime-hygiene.sh` 存在并可执行

7. `scripts/verify-phase1.sh`
   - 增加“legacy snapshot 目录不存在”的检查

8. `scripts/verify-phase5.sh`
   - 增加“packages 仍无业务代码 + 仓库 runtime hygiene 通过”的检查

9. `scripts/verify-all-phases.sh`
   - 串行调用中自动覆盖 hygiene 校验（通过 `check-governance.sh` 间接触发即可）

10. `scripts/resume-refactor.sh`
   - 输出提示从“结构整改阶段恢复”扩展到“迁移后稳定期恢复”

#### C. CI 工作流

11. `.github/workflows/governance.yml`
   - 在 `Verify governance scripts` 或新 step 中新增：
     - `bash scripts/check-runtime-hygiene.sh`
   - 保持 CI fail-fast

12. `.github/workflows/test.yml`
   - 补一个轻量 step：启动测试前先跑 hygiene（推荐）
   - 避免测试 job 在带残留目录的仓库状态下继续执行

#### D. 文档

13. `README.md`
   - 新增一节：**Post-migration stabilization rules**
   - 明确：
     - `apps/web` / `apps/api` 是唯一代码真源
     - 不提交 venv、coverage、logs、test-results、nested repo snapshot
     - 本地清理命令与验证命令

14. `AGENTS.md`
   - 新增规则：
     - 禁止提交运行时产物
     - 禁止提交嵌套旧仓库快照
     - 改动 `apps/*` 后必须运行 hygiene check

15. `docs/governance/migration-conditions.md`
   - 从“迁移准入条件”更新为两部分：
     - 迁移已完成的前提
     - 迁移后稳定期的持续门禁
   - 保留历史背景，但新增“Do not reintroduce legacy paths”与“Do not commit local environments / reports”

16. `docs/development/testing-strategy.md`
   - 新增“测试产物不入库”规则：
     - `test-results/`
     - `playwright-report/`
     - `.coverage`
     - `htmlcov/`
     - `.pytest_cache/`

17. `docs/governance/code-boundary-baseline.md`
   - 增加一条仓库 hygiene 约束说明：
     - 代码边界之外，运行时产物、覆盖率、local venv 也必须被门禁拒绝

---

### 6.3 必删文件 / 目录（Git 删除）

> 这部分建议直接用 `git rm -r` 处理，避免只是本地删除但 Git 仍跟踪。

#### A. 根目录残留

1. `git rm -r logs/archive`
2. `git rm -r test-results`
3. `git rm -r uploads`（如果无必须保留的样例文件）
4. `git rm -r scholar-ai`

#### B. `apps/web` 残留

5. `git rm -r apps/web/test-results`
6. `git rm apps/web/frontend.log`
7. `git rm -r apps/web/.github`（空目录不会保留，若有内容则删）
8. `git rm -r apps/web/packages`（若仅为空壳 temp-package）

#### C. `apps/api` 残留

9. `git rm -r apps/api/venv`
10. `git rm -r apps/api/htmlcov`
11. `git rm -r apps/api/htmlcov_reranker`
12. `git rm -r apps/api/alembic/__pycache__`
13. `git rm -r apps/api/app/__pycache__`
14. `git rm -r apps/api/tests/__pycache__`

> 若 `git rm` 因为目录已未跟踪而失败，改用 `rm -rf` 本地清理，并确保 `.gitignore` 已覆盖。

---

## 7. 推荐执行步骤（可直接照着做）

### Step 0：拉最新主线并建分支

```bash
git checkout main
git pull origin main
git switch -c chore/pr4-post-migration-stabilization
```

### Step 1：先做基线验证

```bash
bash scripts/check-governance.sh
bash scripts/verify-all-phases.sh
```

### Step 2：删除已跟踪残留

```bash
git rm -r logs/archive || true
git rm -r test-results || true
git rm -r uploads || true
git rm -r scholar-ai || true

git rm -r apps/web/test-results || true
git rm apps/web/frontend.log || true
git rm -r apps/web/.github || true
git rm -r apps/web/packages || true

git rm -r apps/api/venv || true
git rm -r apps/api/htmlcov || true
git rm -r apps/api/htmlcov_reranker || true
git rm -r apps/api/alembic/__pycache__ || true
git rm -r apps/api/app/__pycache__ || true
git rm -r apps/api/tests/__pycache__ || true
```

### Step 3：补 ignore 与清理脚本

1. 修改 `.gitignore`
2. 新增 `scripts/check-runtime-hygiene.sh`
3. 新增 `scripts/clean-repo-artifacts.sh`

### Step 4：把 hygiene 接入治理链路

1. 修改 `scripts/check-governance.sh`
2. 修改 `scripts/check-structure-boundaries.sh`
3. 视需要修改 `scripts/verify-phase0.sh`、`verify-phase1.sh`、`verify-phase5.sh`
4. 修改 `.github/workflows/governance.yml`
5. 视需要修改 `.github/workflows/test.yml`

### Step 5：补 root 入口

1. 修改 `package.json`
2. 修改 `Makefile`

### Step 6：更新文档

1. 修改 `README.md`
2. 修改 `AGENTS.md`
3. 修改 `docs/governance/migration-conditions.md`
4. 修改 `docs/development/testing-strategy.md`
5. 修改 `docs/governance/code-boundary-baseline.md`
6. 新增 `docs/reports/post-migration-stabilization-checklist.md`

### Step 7：执行本地验收

见第 8 节命令。

### Step 8：提交建议

建议至少拆成 4 个 commit：

1. `chore: remove tracked runtime artifacts after apps migration`
2. `chore: add runtime hygiene checks and cleanup scripts`
3. `chore: wire post-migration hygiene into governance and ci`
4. `docs: add post-migration stabilization rules and checklist`

---

## 8. 验收清单

### 8.1 目录与残留

- [ ] 根目录不再存在 `scholar-ai/backend-python` 嵌套旧仓库副本
- [ ] 根目录不再跟踪 `logs/archive/**`
- [ ] 根目录不再跟踪 `test-results/**`
- [ ] `apps/web` 不再存在 `frontend.log`
- [ ] `apps/web` 不再存在 `test-results/**`
- [ ] `apps/api` 不再存在 `venv/**`
- [ ] `apps/api` 不再存在 `htmlcov/**`
- [ ] `apps/api` 不再存在 `htmlcov_reranker/**`
- [ ] `apps/api` 不再存在已提交的 `__pycache__/**`

### 8.2 门禁

- [ ] `scripts/check-runtime-hygiene.sh` 通过
- [ ] `scripts/check-governance.sh` 通过
- [ ] `scripts/check-structure-boundaries.sh` 通过
- [ ] `scripts/check-code-boundaries.sh` 通过
- [ ] `scripts/verify-all-phases.sh` 通过

### 8.3 前后端

- [ ] `apps/web` type-check 通过
- [ ] `apps/web` test:run 通过
- [ ] `apps/api` 关键单测通过
- [ ] `apps/api` unified search 测试通过

### 8.4 文档

- [ ] README 已加入迁移后稳定期说明
- [ ] AGENTS 已加入 artifact / nested snapshot 禁令
- [ ] migration-conditions 文档已切换为“迁移后持续门禁”视角

---

## 9. 验收命令

### 9.1 新增 hygiene 检查

```bash
bash scripts/check-runtime-hygiene.sh
```

### 9.2 治理与阶段验收

```bash
bash scripts/check-doc-governance.sh
bash scripts/check-structure-boundaries.sh
bash scripts/check-code-boundaries.sh
bash scripts/check-governance.sh
bash scripts/verify-phase0.sh
bash scripts/verify-phase1.sh
bash scripts/verify-phase2.sh
bash scripts/verify-phase3.sh
bash scripts/verify-phase4.sh
bash scripts/verify-phase5.sh
bash scripts/verify-all-phases.sh
```

### 9.3 前端

```bash
cd apps/web && npm install
cd apps/web && npm run type-check
cd apps/web && npm run test:run
cd ../..
```

### 9.4 后端

```bash
cd apps/api && pytest -q tests/unit/test_services.py --maxfail=1
cd apps/api && pytest -q tests/test_unified_search.py --maxfail=1
cd ../..
```

### 9.5 PR-4 总验证（推荐）

```bash
bash scripts/check-runtime-hygiene.sh && \
bash scripts/check-governance.sh && \
bash scripts/verify-all-phases.sh && \
(cd apps/web && npm run type-check && npm run test:run) && \
(cd apps/api && pytest -q tests/unit/test_services.py --maxfail=1 && pytest -q tests/test_unified_search.py --maxfail=1)
```

---

## 10. 回滚方案

### 10.1 开始前打标记

```bash
git tag pre-pr4-post-migration-stabilization
git branch backup/pre-pr4-post-migration-stabilization
```

### 10.2 PR 未合并时放弃

```bash
git switch main
git branch -D chore/pr4-post-migration-stabilization
```

### 10.3 本地改乱时回滚

```bash
git reset --hard pre-pr4-post-migration-stabilization
git clean -fd
```

### 10.4 PR 已合并后的回滚

```bash
git checkout -b revert/pr4-post-migration-stabilization
git revert -m 1 <merge_commit_sha>
```

---

## 11. 建议的 PR 描述摘要

### 标题建议

`chore: stabilize repository after apps physical migration`

### PR Summary 建议

- remove tracked runtime artifacts, local venv, coverage reports, and nested legacy repo snapshot
- add runtime hygiene checks and cleanup script
- wire post-migration hygiene into governance and CI
- update README / AGENTS / migration docs for post-migration stabilization period

---

## 12. PR-4 完成后的下一步

PR-4 完成后，仓库层面就基本稳定了。下一阶段建议直接进入：

1. `packages/types` 首批共享 DTO 抽取
2. `packages/sdk` 首批 API client 抽取
3. KB Workspace 重构
4. Chat Workspace 重构

也就是说，PR-4 是“结构稳定化”的最后一步；做完后就该回到真正影响体验的业务主线。
