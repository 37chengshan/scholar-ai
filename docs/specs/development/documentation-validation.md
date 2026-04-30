# Documentation Validation

## Purpose

定义 ScholarAI 文档治理的可执行校验标准，确保文档可读、可导航、可长期维护。

## Scope

覆盖核心治理文档、架构文档、开发流程文档，以及 `docs/specs/` 与 `docs/plans/` 下关键入口的本地链接有效性检查。

## Source of Truth

- 文档地图：docs/README.md
- 架构入口：architecture.md
- 协作地图：AGENTS.md
- 校验脚本：scripts/check-doc-governance.sh
- 总治理脚本：scripts/check-governance.sh

## Rules

核心校验项：

- 核心治理文档必须存在。
- `docs/` 根层只能保留 `README.md`、`specs/`、`plans/` 三类入口。
- `docs/README.md` 必须能定位当前产品主线。
- `docs/plans/README.md` 必须能定位当前 active 版本计划入口。
- `docs/specs/README.md` 必须说明规范型文档如何归档。
- 核心治理文档必须包含统一章节：
  - Purpose
  - Scope
  - Source of Truth
  - Rules
  - Required Updates
  - Verification
  - Open Questions
- 关键交叉引用必须存在（例如 PR 流程与测试策略互链）。
- 治理关键文档集中的 markdown 本地链接必须可解析到真实路径。

文档书写约束：

- 优先短章节与可扫描列表，避免长段落堆叠。
- 一个规则只在一个 canonical 文档定义，其它位置通过链接引用。
- 兼容入口文件必须显式标注 canonical 路径，禁止复制全文。

失败处理策略：

- 文档结构缺失：补齐章节后再合并。
- 链接失效：修复目标路径或更新引用。
- 规则冲突：以 Source of Truth 指向的文档为准，清理重复定义。

## Required Updates

- 新增核心文档：更新 scripts/check-doc-governance.sh 的 required_docs。
- 调整统一章节：更新 scripts/check-doc-governance.sh 的 required_sections。
- 调整文档目录：更新 docs/README.md 的结构索引。
- 调整 `docs/specs` 或 `docs/plans` 根层结构：同步更新本文件和 `scripts/check-doc-governance.sh`。
- 切换当前产品主线：同步更新 docs/README.md 与 docs/plans/README.md。

## Verification

本地：

- bash scripts/check-doc-governance.sh

CI：

- .github/workflows/governance-baseline.yml

抽样复核：

- 随机抽取 3 个 docs 文件，验证本地链接、章节骨架、回链一致性。

## Open Questions

- 是否需要引入 markdown lint 规则（标题层级、空行、列表缩进）作为下一阶段门禁。
- 是否需要按文档域增加 owner 字段和过期时间戳。
