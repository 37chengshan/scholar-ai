## Summary

- 问题背景与目标：
- 本次改动范围（代码/文档/流程）：
- 关键变更点：

## Verification

- [ ] Governance deep checks 已执行（`bash scripts/check-governance.sh`）
- [ ] 文档结构与链接校验已执行（`bash scripts/check-doc-governance.sh`）
- [ ] 代码层边界校验已执行（`bash scripts/check-code-boundaries.sh`）

Commands and outcomes:

```text
填写执行命令与关键结果
例如：bash scripts/check-code-boundaries.sh
例如：cd backend-python && pytest -q tests/unit/test_services.py --maxfail=1
```

## Contract and Resource Impact

- [ ] 无 API 契约变更
- [ ] 已更新 docs/architecture/api-contract.md
- [ ] 已更新 docs/domain/resources.md
- [ ] 已记录 breaking change 或迁移风险

## Governance Checklist

- [ ] 未提交 *.pid、cookies.txt、临时日志、测试产物
- [ ] 未新增 doc、tmp、legacy、_new、平行实现目录
- [ ] 已按需更新 architecture.md
- [ ] 已按需更新 AGENTS.md

## Review Checklist

- [ ] 前端页面未直接请求 API（经由 service/hooks）
- [ ] backend router 未包含业务编排
- [ ] schema/DTO 无跨目录重复定义
- [ ] 新接口响应符合统一格式

## Risks and Rollback

- 风险等级：
- 回滚路径：
