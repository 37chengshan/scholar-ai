# Code Boundary Baseline

## Purpose

记录当前代码层边界治理基线，用于阻止新增分层违规并逐步消减历史技术债。

## Scope

覆盖 frontend 页面/组件 API 访问边界与 backend API 层数据库操作边界。

## Source of Truth

- 脚本：scripts/check-code-boundaries.sh
- 编码规范：docs/development/coding-standards.md
- 系统边界：docs/architecture/system-overview.md

## Rules

前端边界规则：

- frontend/src/app/pages 与 frontend/src/app/components 不得直接使用 apiClient、fetch、EventSource。
- 页面/组件访问后端必须通过 frontend/src/services 或 frontend/src/app/hooks。

后端边界规则：

- backend-python/app/api 中新增文件默认禁止直接进行 db.execute/db.add/db.delete/db.flush/db.refresh/db.commit。
- 历史遗留文件暂时允许，必须在本清单登记，后续逐步迁移到 service 层。

当前允许后端 API 直连数据库文件（历史基线）：

- backend-python/app/api/annotations.py
- backend-python/app/api/compare.py
- backend-python/app/api/dashboard.py
- backend-python/app/api/imports/batches.py
- backend-python/app/api/imports/dedupe.py
- backend-python/app/api/imports/jobs.py
- backend-python/app/api/kb/kb_crud.py
- backend-python/app/api/kb/kb_import.py
- backend-python/app/api/kb/kb_papers.py
- backend-python/app/api/notes.py
- backend-python/app/api/papers/paper_status.py
- backend-python/app/api/papers/paper_upload.py
- backend-python/app/api/projects.py
- backend-python/app/api/reading_progress.py
- backend-python/app/api/tasks.py
- backend-python/app/api/uploads.py
- backend-python/app/api/users.py

## Required Updates

- 新增允许文件：必须先提交迁移计划并更新本文件。
- 文件完成迁移：必须从允许清单删除并在 PR 说明中标记。

## Verification

- bash scripts/check-code-boundaries.sh
- bash scripts/check-governance.sh

## Open Questions

- 是否将后端允许清单拆分为按业务域治理的迁移里程碑。
- 是否在下一阶段引入 import 依赖方向静态检查（router->service->model）。
