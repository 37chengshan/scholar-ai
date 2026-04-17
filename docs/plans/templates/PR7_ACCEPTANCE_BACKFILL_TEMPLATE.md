# PR7 Acceptance Backfill Template

> 用途：为 PR7 的每个 slice 提供统一的验收回填记录，确保实现、验证、评审、风险与回滚信息可追溯。

## 基本信息

- slice: `P7-A | P7-B | P7-C`
- 日期: `YYYY-MM-DD`
- 负责人: `@owner`
- 评审人: `@reviewer`
- 状态: `draft | reviewed | accepted | blocked`

## 变更范围

- changed_files:
  - `apps/api/app/...`
  - `apps/api/tests/...`
  - `docs/...` (如有)
- 需求映射:
  - `PR7_PR8_Chat稳定性_AgentNative_RAG升级实施方案.md` 中的对应条目

## 验收标准与结果

- AC-1:
  - 描述:
  - 结果: `pass | fail | partial`
  - 证据:
- AC-2:
  - 描述:
  - 结果: `pass | fail | partial`
  - 证据:
- AC-3:
  - 描述:
  - 结果: `pass | fail | partial`
  - 证据:

## 验证执行记录

- verification:
  - 命令:
    - `cd apps/api && pytest -q ... --maxfail=1`
    - `bash scripts/check-governance.sh` (如适用)
  - 输出摘要:
  - 失败与修复（如有）:

## 证据提交

- evidence_commits:
  - `<commit_sha> <title>`
  - `<commit_sha> <title>`
- PR 评论或审查链接:
  - `<link-or-note>`

## 风险与回滚

- risk:
  - 风险项:
  - 影响面:
  - 缓解措施:
- rollback:
  - 回滚触发条件:
  - 回滚步骤:
  - 回滚验证:

## 结论

- reviewer_decision: `approve | request-changes | blocked`
- 结论说明:
- 后续动作:
