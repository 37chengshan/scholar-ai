# 02 Backend Full Audit (Phase0)

## 1. Audit Scope

- 目标: 核验 release gate 报告与后端实现一致性，确认 P0/P1 风险。
- 范围: apps/api/app/api/chat.py、session 归属校验链路、chat fast path 合同单测。

## 2. Key Checks

### 2.1 Release Gate Alignment

- 检查项:
  - fast path 相关逻辑存在
  - done payload response_type 字段存在
- 结果: 通过（代码存在对应分支与字段）。

### 2.2 Session Ownership (P0-B)

- 发现: /api/v1/chat/stream 在 request.session_id 存在时，仅获取 session，未校验 session.user_id 与 current user。
- 风险: 存在跨用户 session 访问窗口。
- 处理: 已修复。
  - 当 session.user_id != user_id 时，返回 403 forbidden。
  - 修复文件: apps/api/app/api/chat.py

### 2.3 Unit Test Contract

- 新增/更新:
  - chat fast path 单测补充 owner 校验行为。
  - 由于 chat_stream 统一 error-stream 返回，测试按 error/done 事件断言 forbidden。
- 验证:
  - python3 -m pytest tests/unit/test_chat_fast_path.py -q
  - 结果: 7 passed。

## 3. Full Unit Status

- 命令: python3 -m pytest tests/unit -q
- 结果: 134 failed, 1071 passed, 1 skipped, 57 errors。
- 结论: 当前仓库不满足“后端全量 unit 全绿”。

## 4. Failure Clusters (Non-Phase0 New Defects)

- 依赖与模型环境类:
  - Qwen3VL/Reranker/Transformers 本地模型与 mock 适配差异
- 路由/依赖注入类:
  - papers/tasks/uploads 相关 ImportError/FastAPI route errors
- 工具与存储契约类:
  - query_tools/page_clustering/upload_session 等接口与测试预期漂移

## 5. Backend Gate Verdict

- P0-B（session ownership）: PASS（已修复并单测覆盖）。
- fast path 合同: PASS（目标单测通过）。
- 全量 unit: FAIL（历史存量失败，需 Phase1 专项治理）。
