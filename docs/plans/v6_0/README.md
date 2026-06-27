# v6.0 Plans

ScholarAI v6.0 是 v5.x 之后的前端精修与前后端链路可信度迭代。它不重建已有系统,而是优先把已识别的遗留问题收口到真实代码路径:

- 前端:设计 token 消费层收口、可访问性必修项、关键工作区状态视觉一致性、Dashboard/Analytics/Upload 等高频页面细节修复。
- 后端:检索链路禁止 fabricated evidence、配置解析可靠性、RAG prompt helper 公共 API 稳定性。
- 前后端结合:修复 Dashboard recent papers 客户端与 axios envelope unwrap 契约不一致的问题。

## Directory Layout

- `active/`: v6.0 执行中的计划与任务拆解
- `search/`: v6.0 调研输入与缺口扫描
- `reports/`: v6.0 审核、验证、评分与 closeout 报告
- `complete/`: 已完成并归档的 v6.0 计划材料

## Current Report

- `reports/2026-06-20_v6_0_multidimensional_audit.md`

## Version Rules

1. v6.0 不新增平行前端或后端实现路径;前端仍在 `apps/web`,后端仍在 `apps/api`。
2. UI 改动必须优先消费 `docs/specs/design/frontend/DESIGN_SYSTEM.md` 已定义 token,不得把 inline color literal 当作新主题。
3. RAG/检索链路不得向用户返回 fabricated evidence;未接真实索引的检索通道必须安全空降级并通过 diagnostics 暴露。
4. 分数达到 91 分以上才允许进入 PR 收尾;评分必须同时记录验证命令和残余风险。
