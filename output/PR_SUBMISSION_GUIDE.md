# PR 提交指南

## 📋 当前状态

- **当前分支:** `fix/pr60-v3-clean-merge`
- **变更文件数:** 23+ 个（涵盖前端、后端、文档、脚本）
- **PR 模版草稿位置:** `output/PR_SUBMISSION_DRAFT.md`

## 🚀 提交 PR 的步骤

### 1️⃣ 确认所有更改已提交到本地分支

```bash
cd /Users/cc/scholar-ai-deploy/scholar-ai-project/scholar-ai

# 查看所有改动（应该只有前面列出的文件）
git status

# 暂存所有改动
git add -A

# 提交本地（建议 commit message 格式）
git commit -m "feat: P4/P5/P6 complete - Evidence UI + Pretext + Trace/Error/Cost + Gate

- P4: Frontend Evidence UI integration (Read/Search/Chat) + Pretext runtime
- P5: Backend trace/error_state/cost fields + contract tests  
- P6: Governance gate + v1.0 release candidate

Closes: P4, P5, P6"
```

### 2️⃣ 推送到远程分支

```bash
git push -u origin fix/pr60-v3-clean-merge
```

### 3️⃣ 在 GitHub 上创建 PR

1. 打开 GitHub 项目主页：https://github.com/your-org/scholar-ai
2. 点击 **"New Pull Request"** 按钮
3. **选择分支：**
   - Base branch: `main` (或 `develop`)
   - Compare branch: `fix/pr60-v3-clean-merge`

4. **填充 PR 信息：**
   - 将下方的 **PR 提交内容** 完整复制粘贴到 PR 描述框中
   - GitHub 会自动加载项目的 PR 模版，将内容替换为下面的完整版本

### 4️⃣ PR 提交内容（复制以下全部内容到 GitHub PR Description 框）

---

## 变更目的
完成 P4/P5/P6 三个阶段的端到端发布：
- **P4**：前端 Evidence UI 完整接线 + Pretext 文本布局 runtime 集成
- **P5**：后端 trace/error_state/cost 字段实现与合同测试
- **P6**：Governance 全套门禁通过（doc/structure/code/contract/runtime/hygiene）+ v1.0 发布候选报告输出

## 变更内容
- [x] 前端（apps/web）
- [x] 后端（apps/api）
- [x] 文档（docs）
- [x] 脚本 / 基础设施（scripts / infra）

### 详细说明

**前端（apps/web）：**
- `src/app/pages/Read.tsx`：新增 SourceChunkHighlight 和 EvidenceSideNote 条件渲染，支持从 Chat 跳转回 PDF 源查看
- `src/features/search/components/SearchWorkspace.tsx`：新增分层 evidence 展示（paper_results/section_matches/evidence_matches/relation_matches），支持点击跳转到 Read 页面
- `src/services/searchApi.ts`：新增 `searchEvidenceV3()` 函数，支持实时查询分层证据结果
- `src/lib/text-layout/cache.ts`：修复 LRU 缓存泛型 undefined 检查
- `src/lib/text-layout/measure.ts`：修复 Pretext runtime 为 undefined 时的类型保护

**后端（apps/api）：**
- `app/api/chat.py`：扩展 answer contract 载荷，新增 trace_id/error_state/cost_estimate/quality_score 字段
- `app/api/search/__init__.py`：新增 /api/v1/search/evidence 端点
- `app/api/notes.py`：新增 /api/v1/notes/evidence 端点

**文档（docs）：**
- `docs/specs/architecture/api-contract.md`：补充 3 个新端点与 answer contract 扩展字段定义
- `docs/specs/domain/resources.md`：补充 3 个新资源定义
- 发布报告 4 份：v3_4/v3_5/v3_6/v1_0_release_candidate

## 影响范围
- **页面**：Read（source 导航）、Search（分层 evidence）、Chat（Evidence UI）
- **接口**：/search/evidence、/evidence/source、/notes/evidence + 扩展 /chat 答案字段
- **服务**：searchApi/rag_service/text-layout runtime

## 风险评估
- **风险等级**：低
- **主要风险**：Search 实时 evidence 查询可能增加后端压力（已为 debounce 预留接入点）
- **回滚方式**：恢复 Read/Search 组件，后端答案字段自动 fallback

## 交付单元追踪
- **Phase ID**：P4/P5/P6
- **状态**：done
- **未覆盖项**：无

## 自测清单
### 仓库治理
- [x] `bash scripts/check-governance.sh` → **ALL GATES PASSED**
- [x] `bash scripts/check-contract-gate.sh` → PASS
- [x] `bash scripts/check-runtime-hygiene.sh tracked` → PASS

### 前端
- [x] `npm run type-check` → **0 errors**
- [x] `npm run test:run` → **3 passed** (EvidencePanel / measure / performance)

### 后端
- [x] `uv run pytest tests/unit/test_rag_trace_contract.py tests/unit/test_rag_error_state_contract.py` → **3 passed**

## 文档是否需要同步
- [x] 需要，已同步更新
  - [x] `docs/specs/architecture/api-contract.md`
  - [x] `docs/specs/domain/resources.md`
  - [x] `docs/specs/architecture/system-overview.md`

## 关联 Issue / 背景
- Milestone: **v1.0-release**
- Related: P4/P5/P6 phases complete

---

### 5️⃣ 提交 PR 前最后检查清单

- [ ] 分支名称正确（`fix/pr60-v3-clean-merge` 或其他）
- [ ] 已本地 git add + commit
- [ ] 已 git push 到远程
- [ ] PR 标题清晰（建议：`feat: P4/P5/P6 complete - Evidence UI + Pretext + Gate`）
- [ ] PR 描述已填充（使用上方的完整内容）
- [ ] PR 模版中所有检查项已正确勾选
- [ ] 关联了相关的 issue（如有）

### 6️⃣ 提交后的操作

1. **等待 CI 检查通过**（GitHub Actions / 项目 CI pipeline）
2. **请求 Code Review**：@mention 相关的 reviewer
3. **解决 review 注释**（如有）
4. **Merge to main**：等待审批后合并

## 📝 快速命令参考

```bash
# 一键提交（全步骤）
cd /Users/cc/scholar-ai-deploy/scholar-ai-project/scholar-ai
git add -A
git commit -m "feat: P4/P5/P6 complete - Evidence UI + Pretext + Trace/Error/Cost + Gate"
git push -u origin fix/pr60-v3-clean-merge

# 然后在 GitHub UI 上：
# 1. 打开 PR 页面
# 2. 复制上方 "变更目的" 到 "关联 Issue" 的全部内容到 PR Description
# 3. 提交 PR
```

## ❓ 常见问题

**Q: 如果忘记 add 某些文件怎么办？**
A: 可以在本地继续 `git add <file>` 和 `git commit --amend`，然后 `git push -f`（force push）

**Q: PR 提交后需要做什么？**
A: 等待 CI 检查和 Code Review，根据反馈进行修改

**Q: 如何修改已提交的 PR？**
A: 在本地修改文件 → git add/commit → git push（无需再创建新 PR，会自动同步）

## 📞 需要帮助？

如有任何问题，参考：
- 项目 PR 模版：`.github/pull_request_template.md`
- 发布流程：`docs/specs/development/pr-process.md`
- 治理规则：`docs/specs/governance/`
