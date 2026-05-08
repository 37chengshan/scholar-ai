# Verified Residual Gaps Report

> 日期：2026-05-07  
> 范围：phase-text round2 浏览器复验  
> 性质：已验证残余问题清单，不是 release verdict

## 1. 证据来源

1. `docs/plans/phase-text/2026-05-07_frontend_page_test_record_round2.json`
2. `docs/plans/v4_0/reports/2026-05-04_v4_0_phase_2_closeout_report.md`
3. `docs/plans/v4_0/reports/2026-05-04_v4_0_top_level_status_report.md`

## 2. 已验证残余问题

### 2.1 Knowledge Base 列表与侧边栏仍暴露测试式种子内容

- status: open
- severity: low
- scope: `/knowledge-bases`, global sidebar recent KB
- symptom: 列表卡片和最近知识库区仍展示 `Phase2-Online-Verify-*` 一类历史验证名称与英文测试描述。
- evidence:
  - `docs/plans/phase-text/2026-05-07_frontend_page_test_record_round2.json`
- impact: 影响 demo-visible 文案质量，内部测试种子直接暴露给用户。
- fix direction: 统一替换种子数据，或在产品视图中隐藏显式测试 fixture。

### 2.2 Compare-scoped chat 仍以 summary-level evidence 为主

- status: open
- severity: medium
- scope: `/compare` -> `/chat` handoff
- symptom: Compare 页面与 Chat 互通已恢复，但当比较语料缺少更强方法/结果证据时，回答仍会回落到谨慎 abstain 或 summary-only support。
- evidence:
  - `docs/plans/phase-text/2026-05-07_frontend_page_test_record_round2.json`
- impact: 页面链路可用，但跨论文比较的答案质量不够稳定。
- fix direction: 补强 compare 语料路由与证据选择，避免只回到摘要级证据。

### 2.3 Reset-password 的 real-token 成功态与过期态仍缺浏览器证据

- status: open
- severity: medium
- scope: `/reset-password?token=...`
- symptom: 当前已验证缺 token 跳转和本地表单校验，但还没有用真实一次性重置 token 走完整的成功态和失效态。
- evidence:
  - `docs/plans/phase-text/2026-05-07_frontend_page_test_record_round2.json`
- impact: 当前无法证明重置密码后端链路在真实 token 下的最终用户体验与错误文案是否正确。
- fix direction: 为测试环境生成真实 reset token，分别验证成功重置一次和失效/过期 token 一次。

## 3. 已关闭项

1. `/settings` 和 `/analytics` 的 React 非布尔属性警告已修复。
2. Notes 里历史序列化 JSON 外泄问题已修复。
3. Read / KB / Chat / Compare 的主链路页面跳转与展示已恢复。
4. `/forgot-password` 与 `/reset-password` 的亮红认证卡片外框问题已修复。
5. `/search` 现在已经可以命中已知库内论文 `test_5_pages`，并暴露 `read/chat` CTA。
6. `/settings` 的语言选择现在会持久化到 `localStorage["scholarai-language"]`，重载后不会再退回中文。
7. `/forgot-password` 的无效邮箱输入现在会留在当前页并显示 `邮箱格式不正确`，不会误进入成功态。
8. 显式 scope 的 `/chat?paperId=...` 现在只加载 recent session 列表，不会再经由全局侧栏偷偷拉取无关会话的 message history。

## 4. 结论

当前 `phase-text/` 的残余问题已经收敛到少量明确缺口，不再是文档缺失，而是产品仍有少数可复现 gap。后续测试只需继续清这些已知项，并回填新证据即可。
