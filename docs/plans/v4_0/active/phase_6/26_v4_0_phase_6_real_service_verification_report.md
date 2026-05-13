# Phase 6 Real Service Verification Report

## 目标
验证 Phase 6 相关的真实服务链路已经启动，并通过实际 HTTP 请求检查关键业务路径。

## 环境
- 后端服务：`uvicorn app.main:app --port 8089`
- 数据库：PostgreSQL 已连接
- 图谱：Neo4j 已连接
- Redis：已连接

## 实测过程
### 1. 图谱读接口
请求：`GET /api/v1/graph/nodes?limit=5`

结果：
- HTTP 200
- 返回 5 个真实节点
- 节点类型包含 `Author`、`Method`、`Paper`
- 证明服务端路由、Neo4j 读取和 JSON 响应都正常

### 2. Compare V4 真实业务请求
请求：`POST /api/v1/compare/v4`
- 使用真实数据库中同一用户的两篇 `completed` 论文
- 使用 `Authorization: Bearer <access_token>`
- 请求体包含 `paper_ids`、`question` 和 `dimensions`

结果：
- HTTP 500
- 服务端日志显示真实失败点为 `MilvusException`
- 错误信息：`Fail connecting to server on localhost:19530, illegal connection params or server unavailable`

## 真实数据库抽样
- papers 表状态分布：`completed 31`、`failed 24`、`processing 5`
- 已选取同一用户下的两篇 `completed` 论文作为 compare 请求输入

## 结论
- 真实服务已成功启动，并能返回实际图谱数据。
- Phase 6 的 compare 真实路径已经被打通到业务层，但当前运行环境缺少可用的 Milvus 服务，因此 compare/v4 在检索阶段失败，而不是在认证或路由阶段失败。
- 这次验证说明问题是运行时依赖可用性，不是 Phase 6 路由本身未接通。

## 后续建议
1. 启动或修复本地 Milvus，再重跑 `POST /api/v1/compare/v4`。
2. 如需继续验证 review 路径，可用同样方式打真实 review 请求并观察 graph/global synthesis 产物。
3. 把这次 Milvus 失败记录同步到 Phase 6 的后续运维或 closeout 材料中。
