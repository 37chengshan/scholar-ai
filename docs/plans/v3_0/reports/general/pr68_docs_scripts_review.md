# PR #68 Scripts & Docs Review

Reviewer: scripts-docs-reviewer
Date: 2026-05-02
Scope: scripts/, docs/, .tmp_pr_body_phase_i_j_full.md

---

## 1. Script Review: run_phase_j_closeout.py (NEW, +192 lines)

### CLI 参数处理
- argparse 配置正确，所有必需参数均已标记 `required=True`
- `--output-dir` 有合理默认值 (`artifacts/validation-results/phase_j/latest`)

### 错误处理
- **问题 [LOW]**: `_load_json()` 没有 try/except 包装。如果输入文件不存在或 JSON 格式错误，会抛出未捕获的 `FileNotFoundError` 或 `json.JSONDecodeError`，直接 crash 到 stderr。对于 eval 脚本这是可接受的，但建议至少提供友好的错误消息。
- `_academic_run_bundle()` 内部连续读取 6 个 JSON 文件，任一缺失都会 crash，无逐文件错误提示。

### 文件 I/O 安全性
- `_write_json()` 使用 `mkdir(parents=True, exist_ok=True)` 创建输出目录，合理。
- 输出路径来自 CLI 参数，无路径遍历风险（本地 eval 脚本，非 web 暴露）。
- 所有文件读写均指定 `encoding="utf-8"`，良好。

### 硬编码路径/敏感信息
- `ARTIFACTS_ROOT` 和 `ACADEMIC_ROOT` 均基于 `ROOT` 计算，ROOT 来自 `__file__` 解析，合理。
- 无 API key、密码等硬编码敏感信息。

### 代码质量
- 函数长度均在合理范围内 (<50 行)
- 使用了 immutable dataclass 模式 (from comparative_gate)
- 类型注解完整

---

## 2. Script Review: run_phase_j_comparative_gate.py (REWRITE, +587/-117)

### 变更概述
从简单的比较脚本重写为完整的 comparative gate 系统，新增:
- `ThresholdPolicy` frozen dataclass 替代硬编码浮点参数
- 4 级 verdict 体系: pass / warn / fail / experiment-only
- `_safe_float()` / `_safe_bool()` 防御性解析
- `normalize_case_entry()` 统一不同数据源的 entry 格式
- `extract_entries()` 支持 4 种 payload 形态的自动检测
- `_per_bucket_diff()` 按 case_source::task_family 分桶对比
- `render_markdown_summary()` 生成可读报告
- `run_gate()` 作为统一入口函数

### CLI 参数处理
- 新增 `--diff-output`、`--markdown-output`、`--baseline-label`、`--candidate-label`，均有合理默认值
- 保留了原有 `--baseline`、`--candidate`、--output` 的向后兼容

### 错误处理
- **问题 [LOW]**: `_load_json()` 同样无 try/except
- `extract_entries()` 对不支持的 payload 形状抛出明确的 `ValueError`，良好
- `_validate_required_fields()` 返回详细的缺失字段列表，便于调试

### 阈值策略
- `ThresholdPolicy` 使用 frozen dataclass，不可变，良好
- 默认阈值合理: unsupported_regression=3%, citation_regression=0%, latency_ratio=15%, cost_ratio=20%
- `THRESHOLD_DEFAULTS` dict 与 `ThresholdPolicy` 默认值重复定义，可能不同步

### 数值安全
- `_safe_float()` 正确处理 None、空字符串、类型异常
- `_ratio_delta()` 正确处理 baseline=0 的除零情况
- 所有 `round()` 调用精度合理

### 向后兼容
- `compare_runs()` 接口从 4 个浮点参数改为 `ThresholdPolicy` 对象，**破坏了外部调用者**。但因为 `run_gate()` 是新的推荐入口，且该脚本是 eval 工具而非库，影响有限。

### 公开函数导出
- `run_gate()`、`summarize_run()`、`extract_entries()`、`normalize_case_entry()`、`compare_runs()` 均已导出，`run_phase_j_closeout.py` 正确 import 了 `run_gate`。

---

## 3. 文档治理迁移审查

### 迁移完整性
| 旧路径 | 新路径 | 状态 |
|--------|--------|------|
| `docs/architecture/api-contract.md` (-583 行) | `docs/specs/architecture/api-contract.md` | 已迁移并新增 replay-only 内容 |
| `docs/domain/resources.md` (-231 行) | `docs/specs/domain/resources.md` | 已迁移并新增 replay-only 内容 |
| `docs/governance/phase-delivery-ledger.md` (-51 行) | `docs/specs/governance/phase-delivery-ledger.md` | 已迁移并新增 DU-20260430-011 |
| `docs/SMART_EMBEDDING_GUIDE.md` | `docs/specs/reference/api/SMART_EMBEDDING_GUIDE.md` | 已迁移 |
| `docs/reports/*` (多文件) | `docs/plans/v2_0/reports/` 和 `docs/plans/archive/reports/` | 已迁移 |

旧目录 `docs/architecture/`、`docs/domain/`、`docs/governance/` 均已删除，确认无残留。

### 新增规范内容
- `docs/specs/architecture/api-contract.md`: 新增 SSE replay-only 模式规范 (2 条规则)
- `docs/specs/domain/resources.md`: 新增 ChatSession replay-only 约束 (1 条规则)
- `docs/specs/governance/phase-delivery-ledger.md`: 新增 DU-20260430-011 (Phase J closeout)
- `docs/specs/README.md`: 新增 Top-level Contract 段落，明确 docs/ 根层约束

### docs/plans/ 新增报告文件
新增 7 个报告文件到 `docs/plans/v3_0/reports/general/`:
- `2026-05-01_backend_audit_report.md`
- `2026-05-01_backend_system_review.md`
- `2026-05-01_frontend_audit_report.md`
- `2026-05-01_frontend_system_review.md`
- `2026-05-01_infra_audit_report.md`
- `2026-05-01_project_health_score.md`

这些文件符合 `docs/plans/` 目录治理规范。

### PLAN_STATUS.md 更新
Phase J 状态从 `research-required` 更新为 `closeout-complete / verification-passed`，并补充了 closeout 证据路径。

---

## 4. 治理检查结果

| 检查项 | 结果 |
|--------|------|
| `bash scripts/check-doc-governance.sh` | PASSED |
| `bash scripts/check-structure-boundaries.sh` | PASSED |

---

## 5. 问题清单

### CRITICAL
无。

### HIGH
1. **`.tmp_pr_body_phase_i_j_full.md` 不应提交到仓库**
   - 该文件是临时 PR body 草稿，已通过 PR diff 被加入仓库
   - 文件当前被 git tracked 且未被 .gitignore 覆盖
   - 建议: 从 PR 中移除此文件，并添加到 .gitignore

### MEDIUM
2. **`THRESHOLD_DEFAULTS` 与 `ThresholdPolicy` 默认值重复**
   - `run_phase_j_comparative_gate.py` 第 40-47 行定义了 `THRESHOLD_DEFAULTS` dict
   - `ThresholdPolicy` dataclass (第 52-58 行) 有相同的默认值
   - 两处可能不同步，建议删除 `THRESHOLD_DEFAULTS` 或让 `ThresholdPolicy` 从中读取

### LOW
3. **两个脚本的 `_load_json()` 均无错误处理**
   - 作为 eval 工具脚本可接受，但建议至少在 `main()` 入口添加 try/except 提供友好错误消息

4. **`run_phase_j_closeout.py` 的 `main()` 无退出码管理**
   - 如果中间步骤抛出异常，进程以非零退出码退出但无明确错误消息
   - 建议在 main() 中捕获异常并 sys.exit(1)

---

## 6. 结论

脚本质量整体良好，重写后的 comparative gate 架构清晰、防御性编程到位。文档治理迁移完整且通过治理检查。主要阻塞项为 `.tmp_pr_body_phase_i_j_full.md` 不应提交到仓库。
