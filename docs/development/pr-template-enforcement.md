# PR Template Enforcement

## Purpose

阻断空模板 PR、占位符 PR 与未按仓库模板填写的 PR 描述。

## Scope

适用于 scholar-ai 仓库所有由 agent、本地脚本或 GitHub Web UI 创建的 PR。

## Rules

- PR body 必须包含 `.github/pull_request_template.md` 中的核心段落。
- 以下段落必须存在且不能是空占位：
  - `## 变更目的`
  - `## 变更内容`
  - `## 影响范围`
  - `## 风险评估`
  - `## 交付单元追踪`
  - `## 自测清单`
  - `## 文档是否需要同步`
- `## 变更内容` 至少要有一个 `[x]` 模块勾选。
- `## 自测清单` 至少要有一个 `[x]` 的实际执行项。
- `## 文档是否需要同步` 必须明确勾选“`不需要`”或“`需要，已同步更新`”之一。

## Enforcement

- 本地/agent 创建 PR 时，必须使用 `scripts/pr_create_with_template_check.sh`。
- CI 在 pull_request 的 `opened`、`synchronize`、`reopened`、`edited`、`ready_for_review` 事件下执行 `scripts/check-pr-template-body.sh`。
- 任一校验失败都应阻断 PR 合入。

## Verification

- 运行 `bash scripts/check-pr-template-body.sh --body-file <filled-pr-body.md>`。
- 在 GitHub Actions 的 pull_request 流水线中确认 PR 模板校验步骤通过。