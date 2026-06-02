# v5.0 Reports

`v5_0/reports/` 按 phase 分目录存放交付报告。

## 目录结构

```
reports/
├── README.md
├── phase_0/          ← Phase 5.0-0 Foundation
│   └── 2026-05-31_v5_0_phase_0_audit_baseline.md
├── phase_1/          ← Phase 5.0-1 设计系统 v2
│   ├── 2026-05-31_v5_0_phase_1_review_synthesis.md      (综合审查)
│   ├── 2026-05-31_v5_0_phase_1_review_dim_A_design.md   (设计视觉)
│   ├── 2026-05-31_v5_0_phase_1_review_dim_B_a11y.md     (无障碍)
│   ├── 2026-05-31_v5_0_phase_1_review_dim_C_css_eng.md  (CSS 工程)
│   ├── 2026-05-31_v5_0_phase_1_review_dim_D_perf.md     (性能)
│   └── 2026-05-31_v5_0_phase_1_review_dim_E_arch.md     (架构集成)
├── phase_2/          ← (待)
├── ...
└── phase_9/          ← Phase 5.0-9 Release Gate
    └── 2026-06-02_v5_0_phase_9_release_gate_closeout.md
```

## 命名约定

- `YYYY-MM-DD_v5_0_phase_N_<type>.md`
- type: `audit_baseline` / `closeout_report` / `review_synthesis` / `review_dim_X` / `walkthrough` / `benchmark` / `gate_report`

## 规则

1. 每个 phase 的报告只放在对应子目录下，不混放
2. 综合报告 (`review_synthesis`) 与维度报告 (`review_dim_X`) 同级
3. 在报告真实落地前，不允许把 v5.0 写成 release-candidate 或 release-pass
