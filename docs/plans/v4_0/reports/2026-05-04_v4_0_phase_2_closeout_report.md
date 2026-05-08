# v4.0 Phase 2 Closeout Report

> 日期：2026-05-04  
> phase: `4.0-2`  
> status: `closeout-complete`  
> verdict: `demo-ready`

## 1. 结论

Phase 4.0-2 已完成本轮 closeout，结论是 `demo-ready`，不是 `controlled-beta-ready`。

这次 closeout 解决了两个核心问题：

1. phase2 主链现在真实走线上模型：
   - generation: Zhipu `glm-4.6v-flashx`
   - embedding: DashScope `text-embedding-v4`
   - rerank: DashScope `qwen3-rerank`
2. Phase 2 的 walkthrough 不再停留在 `walkthrough-pending`：
   - fresh-state import/search probe 已重新跑通
   - browser walkthrough 已覆盖 landing/login、KB、Read、single-paper Chat、Notes、Compare、upload/import workspace

因此，本 phase 可以从 `asset-ready / walkthrough-pending` 推进到 `walkthrough-complete / demo-ready`。

## 2. 本轮关闭内容

### 2.1 Online provider mainline

以下链路已不再默认落回本地 embedding / rerank factory：

1. import/storage 主链
2. KB search 主链
3. review fallback / retrieval 相关入口

运行态探针确认：

1. embedding provider: `DashScopeEmbeddingProvider`
2. embedding runtime model: `text-embedding-v4`
3. reranker provider: `DashScopeRerankService`
4. reranker runtime model: `qwen3-rerank`
5. generation runtime model: `glm-4.6v-flashx`

### 2.2 Runtime defects fixed

本轮修复的真实阻断点：

1. unified search dedupe 的 `dict` / `SearchResult` 混用导致 500
2. phase2 主链 embedding/rerank wiring 仍落本地 factory
3. Milvus `paper_contents` / `paper_summaries` 维度与 1024 在线向量不一致
4. `paper_chunks` 未回写 SQL，导致 KB `chunkCount` / readiness 假空
5. chunk identity 退化，导致 chunk row 冲突与覆盖
6. summary index 文本超过 Milvus string max length
7. Compare 页面 warm-auth / URL 预选竞态
8. Read -> Chat handoff 复用旧 session，污染单论文 RAG
9. single-paper chat 只做全局召回后裁剪，paper scope 没有下推到真实检索层
10. summary/query 依赖本地 artifact，导致在线主链下单论文摘要型问题假性 abstain
11. KB search state 双存储导致页面复用时残留旧结果
12. evidence panel 的 React key 冲突
13. `new=1` fresh session bootstrap 会清空 handoff draft，导致 Read/Compare/Review 的 `Continue in Chat` 已进入正确作用域但输入框不再预填

### 2.3 Browser-verified feature surfaces

已通过浏览器验证：

1. landing / 介绍页与登录页可以进入
2. Knowledge Base detail readiness
3. KB search -> Read -> evidence highlight
4. Read page source side note / sourceChunkId contract
5. Read -> single-paper Chat handoff 与 composer prefill
6. single-paper Chat 非 abstain 回答恢复
7. Notes panel / evidence save note 持久化与 note editor linked evidence action
8. Compare matrix generation
9. upload/import workspace 可进入，文件上传后能创建 import job 并进入 dedupe decision

## 3. Fresh-state Evidence

### 3.1 Fresh import/search probe

- kb_id: `021c2bef-fe6a-4635-ac05-3a62f439bc6e`
- kb_name: `Phase2-Online-Verify-9fa04d82`
- import_job_id: `imp_7f7b296d0a2a4f5ba4fd8f95`
- terminal status: `completed`
- `paperCount=1`
- `chunkCount=105`
- `search_total=5`

这证明 phase2 的 import -> embedding -> vector write -> KB search 主链在当前分支上是真实可用的。

### 3.2 Browser walkthrough evidence

浏览器 walkthrough 主要围绕以下真实对象完成：

- kb_id: `cf84038c-6cdf-434f-8ec8-c97fe3de396e`
- kb_name: `Phase2-Online-Verify-2b7aa183`
- paper_id (LIMA): `e83c8887-04f8-422f-94d6-bbd304283aa5`
- compare second paper: `142c2950-0a4a-4994-ba9f-28fd422b8caa`
- upload probe import_job_id: `imp_88cbd0e55d4049cf80d34098`

验证结果：

| surface | result | evidence |
|---|---|---|
| landing / login | pass | 公开介绍页可进入；退出登录后回介绍页；介绍页 `登录` CTA 到 `/login` |
| KB readiness | pass | `Phase2-Online-Verify-2b7aa183` 页面显示 `2 Papers / 106 Chunks`，readiness cards healthy |
| KB search -> read | pass | 点击 LIMA summary 命中后打开 `/read/e83c8887-04f8-422f-94d6-bbd304283aa5?page=1&source=evidence&source_id=chunk_7e9a7e7ef7ac5b33624e5679` |
| Read highlight | pass | 右栏显示 `source highlight: chunk_7e9a7e7ef7ac5b33624e5679`，并渲染 evidence side note |
| single-paper Chat | pass | Read -> Continue Ask 后进入 `/chat?paperId=...&handoff=1`，handoff prompt 不再被 `new=1` lifecycle 清空，单论文问题返回 `partial` 而不是 `abstain` |
| Notes | pass | Notes Workspace 中能看到新增 evidence note，打开后 linked evidence、`Open source`、`Continue in Chat` 与编辑区都正常 |
| Compare | pass | 以 LIMA + `Test Paper - Page 1` 生成 compare matrix，cell 级 `p. / Save / Chat` 与 `跨论文洞察` 可见 |
| Upload / import | pass | `test_5_pages.pdf` 上传成功，创建 `imp_88cbd0e55d4049cf80d34098`，worker 将其推进到 `dedupe_check` 并因 `pdf_sha256` 命中进入 dedupe decision |

## 4. Remaining Limitations

当前仍保留到后续 gate 的事项：

1. single-paper Chat 已恢复，但当前回答仍可能是 `partial`，并不是所有 claim 都达到 strong support
2. Review 仍可能返回 `partial / insufficient_evidence`
3. walkthrough 证据仍以 operator-led local controlled beta 为主
4. staging / cloud controlled beta gate 尚未开启
5. 不应把当前状态写成 `controlled-beta-ready`、`public-beta-ready` 或 release-pass

这些限制不再阻断 `demo-ready`，但仍阻断更高一级的放行结论。

## 5. 状态推进

### 5.1 PLAN_STATUS

Phase 2 从：

- `asset-ready / walkthrough-pending`

推进为：

- `walkthrough-complete / demo-ready`

### 5.2 Phase execution plan

`21_v4_0_phase_2_execution_plan.md` 从 `in-progress` 推进为 `done`，因为：

1. WP1-WP5 资产已落地
2. WP6 walkthrough 已真实执行并回填
3. WP7 closeout report 已生成

但其结论仍然只到 `demo-ready`，不越级到 `controlled-beta-ready`。

## 6. Verification

后端：

- `cd apps/api && PYTHONPATH=$PWD .venv/bin/pytest -q tests/unit/test_embedding_factory.py tests/unit/test_reranker_factory.py`
- `cd apps/api && PYTHONPATH=$PWD .venv/bin/pytest -q tests/unit/test_pr7_storage_evidence.py tests/unit/test_storage_manager_embedding_runtime.py tests/unit/test_storage_manager_chunk_rows.py tests/unit/test_section_chunk_alignment.py`
- `cd apps/api && PYTHONPATH=$PWD .venv/bin/pytest -q tests/unit/test_hierarchical_retriever_routing.py tests/unit/test_main_path_service_scope_routing.py tests/unit/test_answer_contract.py tests/unit/test_chat_fast_path.py tests/unit/test_rag_trace_contract.py`
- `python3 /tmp/api_phase2_online_verify.py`

前端：

- `cd apps/web && npm run type-check`
- `cd apps/web && npm run test:run -- src/features/chat/chatHandoff.test.ts src/features/chat/hooks/useChatHandoff.test.tsx`
- browser walkthrough:
  - landing / login
  - KB readiness
  - KB search -> Read -> highlight
  - single-paper Chat
  - Notes
  - Compare
  - upload workspace

治理：

- `bash scripts/check-doc-governance.sh`
- `bash scripts/check-plan-governance.sh`
- `bash scripts/check-phase-tracking.sh`

## 7. Handoff

Phase 3/4/5/6/7 的上游结论：

1. Phase 3 可以消费 Review partial honesty，而不是再假设 review 一定 full-green
2. Phase 4/5 可以在不大改 IA 的前提下继续做前端质感和交互质量
3. Phase 6 只需要在现有 online mainline 上做优化，不要再回开本地双路径
4. Phase 7 若要给 release verdict，必须额外完成 controlled beta gate 与更正式的 evaluation pass
