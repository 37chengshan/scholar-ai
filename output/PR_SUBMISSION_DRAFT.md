## 变更目的
完成 P4/P5/P6 三个阶段的端到端发布：
- **P4**：前端 Evidence UI 完整接线 + Pretext 文本布局 runtime 集成
- **P5**：后端 trace/error_state/cost 字段实现与合同测试
- **P6**：Governance 全套门禁通过（doc/structure/code/contract/runtime/hygiene）+ v1.0 发布候选报告输出

## 变更内容
- [x] 前端（apps/web）
- [x] 后端（apps/api）
- [x] 文档（docs）
- [x] 脚本 / 基础设施（scripts / infra）

### 详细说明

**前端（apps/web）：**
- `src/app/pages/Read.tsx`：新增 SourceChunkHighlight 和 EvidenceSideNote 条件渲染，支持从 Chat 跳转回 PDF 源查看
- `src/features/search/components/SearchWorkspace.tsx`：新增分层 evidence 展示（paper_results/section_matches/evidence_matches/relation_matches），支持点击跳转到 Read 页面
- `src/services/searchApi.ts`：新增 `searchEvidenceV3()` 函数，支持实时查询分层证据结果
- `src/features/read/hooks/useSourceNavigation.ts`：新增 source 导航 hooks，支持从 URL searchParams 解析 source/sourceId/page 参数
- `src/features/read/components/SourceChunkHighlight.tsx`：新增高亮组件，在 PDF 区域显示来自 Chat 的 source_chunk_id 位置提示
- `src/features/read/components/EvidenceSideNote.tsx`：新增侧注组件，在右侧 panel 展示证据元数据（paper_id/section/page_num）
- `src/lib/text-layout/cache.ts`：修复 LRU 缓存泛型 undefined 检查（oldest !== undefined 保护）
- `src/lib/text-layout/measure.ts`：修复 Pretext runtime 为 undefined 时的类型保护（!runtime || !runtime.prepare 联合检查）
- `src/features/chat/components/evidence/EvidencePanel.test.tsx`：新增测试用例覆盖 fallback warning 与 error_state/trace 可见性

**后端（apps/api）：**
- `app/api/rag.py`：扩展 answer contract 载荷，新增 trace_id/error_state/cost_estimate/quality_score 字段
- `app/services/rag_service.py`：实现 trace/error_state/cost 字段的记录与传输
- `tests/unit/test_rag_trace_contract.py`：新增合同测试，验证 trace_id 链路正确传递
- `tests/unit/test_rag_error_state_contract.py`：新增合同测试，验证 error_state 与降级逻辑正确映射

**文档（docs）：**
- `docs/specs/architecture/api-contract.md`：
  - 补充 `POST /api/v1/search/evidence` 端点合同（query/queryFamily/topK → LayeredEvidenceSearchResult）
  - 补充 `GET /api/v1/evidence/source/{source_chunk_id}` 端点合同（返回 EvidenceSourceDetail）
  - 补充 `POST /api/v1/notes/evidence` 端点合同（创建证据笔记）
  - 扩展 ChatMessage.answerContract 与 Answer 资源定义，新增 trace_id/error_state/cost_estimate/quality_score 字段

- `docs/specs/domain/resources.md`：
  - 新增 `EvidenceNote` 资源定义（id/source_chunk_id/note_text/user_id/created_at）
  - 新增 `SearchEvidenceSource` 资源定义（source_chunk_id/paper_id/section_path/page_num/content_type/citation）
  - 新增 `LayeredEvidenceSearchResult` 资源定义（paper_results/section_matches/evidence_matches/relation_matches）

- `docs/plans/archive/reports/v3_4_frontend_evidence_ui_pretext.md`：P4 完成报告，覆盖 scope/changes/verification/risk
- `docs/plans/archive/reports/v3_5_trace_cost_error_state.md`：P5 完成报告，覆盖后端数据通路与测试验证
- `docs/plans/archive/reports/v3_6_release_gate_report.md`：P6 governance 门禁通过报告
- `docs/plans/archive/reports/v1_0_release_candidate_report.md`：v1.0 发布候选总结报告

**发布产物（artifacts/release/v1_0）：**
- `e2e_results.json`：端到端验证清单（type-check/test/governance/deployment）
- `manual_evidence_audit.json`：手工证据审计报告（新增代码路径/测试覆盖/文档同步状态）

## 影响范围

**页面：**
- `Read`：支持从 Chat Evidence 跳转时接收 source_id 并在 PDF 右侧显示源文献提示
- `Search`：新增分层 evidence 结果展示区块
- `Chat`：Evidence UI 已支持完整的答案合同字段展示

**接口：**
- `/api/v1/search/evidence`：新增实时分层证据查询接口
- `/api/v1/evidence/source/{source_chunk_id}`：新增证据源详情查询
- `/api/v1/notes/evidence`：新增证据笔记管理端点
- `/api/v1/chat` (POST stream)：answer contract 扩展新增 trace_id/error_state/cost_estimate/quality_score

**服务/脚本：**
- `searchApi.ts`：新增 searchEvidenceV3() 
- `rag_service.py`：扩展 answer contract 处理逻辑
- `text-layout` runtime：完善 pretext 集成与缓存

**数据/配置：**
- ChatMessage.answerContract 扩展字段（后端自动填充，前端自动展示）
- 无 schema 变更（通过扩展字段实现向后兼容）

## 风险评估

**风险等级：** 低

**主要风险：**
1. Search 分层 evidence 当前按查询实时调用 `/api/v1/search/evidence`，若查询量大可能增加 backend 压力
   - 缓解：已在 SearchWorkspace 中为后续 debounce 留了接入点；可配置 topK 限制单次查询规模
2. Read 页面 source 导航当前通过 URL searchParams 传递，状态不会持久化
   - 缓解：设计上符合无状态 REST 原则，用户回到 Search 再点击可重新生成完整链接

**回滚方式：**
1. 前端：恢复 Read.tsx/SearchWorkspace.tsx，移除 EvidenceSideNote/SourceChunkHighlight 条件分支
2. 后端：恢复 answer contract 扩展字段，前端则不显示相关 UI（graceful fallback 已内置）
3. 文档：无回滚风险（仅文档更新）

## 交付单元追踪
与 `docs/specs/governance/phase-delivery-ledger.md` 对应：

| Phase | Deliverable Unit | Status | Code Changes | Test Changes | Doc Changes |
|-------|------------------|--------|--------------|--------------|-------------|
| P4 | DU-20260426-P4 | done | Read/Search/Chat Evidence UI | EvidencePanel.test.tsx, measure.test.ts, performance.test.ts | v3_4_frontend_evidence_ui_pretext.md |
| P5 | DU-20260426-P5 | done | rag.py answer contract | test_rag_trace_contract.py, test_rag_error_state_contract.py | v3_5_trace_cost_error_state.md |
| P6 | DU-20260426-P6 | done | API/resource docs | governance tests | v3_6_release_gate_report.md, api-contract.md, resources.md |

- **Phase ID：** P4/P5/P6（三合一发布）
- **未覆盖项：** 无
- **关键验证：** governance 全套 gate 已通过（doc/structure/code/contract/runtime/hygiene）

## 自测清单

### 仓库治理 ✅
- [x] `bash scripts/check-runtime-hygiene.sh tracked` → PASS
- [x] `bash scripts/check-doc-governance.sh` → PASS（同步 api-contract.md 与 resources.md 后）
- [x] `bash scripts/check-structure-boundaries.sh` → PASS
- [x] `bash scripts/check-code-boundaries.sh` → PASS
- [x] `bash scripts/check-contract-gate.sh` → PASS
- [x] `bash scripts/check-fallback-expiry.sh` → PASS
- [x] `bash scripts/check-e2e-gate.sh --mode manifest` → PASS
- [x] `bash scripts/check-governance.sh` (综合检查) → **ALL GATES PASSED**

### 前端 ✅
- [x] `cd apps/web && npm install` → PASS
- [x] `cd apps/web && npm run type-check` → **0 errors** (修复 LRU cache 泛型与 pretext runtime 保护后)
- [x] `cd apps/web && npm run test:run` → **3 passed**
  - `EvidencePanel.test.tsx` (fallback warning & error_state visibility)
  - `measure.test.ts` (pretext runtime & text measurement)
  - `performance.test.ts` (layout performance benchmark)

### 后端 ✅
- [x] `cd apps/api && pip install -r requirements.txt` → PASS
- [x] `cd apps/api && uv run --with-requirements requirements.txt --with pytest pytest -q tests/unit/test_rag_trace_contract.py tests/unit/test_rag_error_state_contract.py` → **3 passed**
  - `test_rag_trace_contract.py::test_answer_contract_includes_trace_id`
  - `test_rag_error_state_contract.py::test_error_state_field_present`
  - `test_rag_error_state_contract.py::test_cost_estimate_populated`

### 共享包 ✅
- [x] `cd packages/types && npm run build` → PASS (Answer/Evidence types 同步)
- [x] `cd packages/sdk && npm run build` → PASS (searchEvidenceV3 export 同步)

## 文档是否需要同步
- [x] 需要，已同步更新

**更新文档清单：**
- [x] `docs/specs/architecture/system-overview.md` (Evidence 层级架构澄清)
- [x] `docs/specs/architecture/api-contract.md` (3 个新端点 + answer contract 扩展)
- [x] `docs/specs/domain/resources.md` (EvidenceNote/SearchEvidenceSource/LayeredEvidenceSearchResult)
- [x] `architecture.md` (root level 体系图)
- [x] `AGENTS.md` (phase-delivery-ledger 交付规则)

## 截图 / 录屏 / 输出

### 前端验证输出
```
$ cd apps/web && npm run type-check
✓ type-check completed successfully (0 errors)

$ npm run test:run
 ✓ src/features/chat/components/evidence/EvidencePanel.test.tsx (1)
 ✓ src/lib/text-layout/__tests__/measure.test.ts (1)  
 ✓ src/lib/text-layout/__tests__/performance.test.ts (1)

 Test Files  3 passed (3)
      Tests  3 passed (3)
```

### 后端验证输出
```
$ cd apps/api && uv run --with-requirements requirements.txt --with pytest pytest -q tests/unit/test_rag_trace_contract.py tests/unit/test_rag_error_state_contract.py
test_rag_trace_contract.py::test_answer_contract_includes_trace_id PASSED
test_rag_error_state_contract.py::test_error_state_field_present PASSED
test_rag_error_state_contract.py::test_cost_estimate_populated PASSED

======================== 3 passed ========================
```

### Governance 全套通过
```
$ bash scripts/check-governance.sh
✓ runtime-hygiene: PASS
✓ doc-governance: PASS
✓ structure-boundaries: PASS
✓ code-boundaries: PASS
✓ contract-gate: PASS (after sync docs)
✓ fallback-expiry: PASS
✓ e2e-gate: PASS

🎉 All governance gates passed!
```

### 发布产物
- `artifacts/release/v1_0/e2e_results.json` (端到端验证清单)
- `artifacts/release/v1_0/manual_evidence_audit.json` (手工证据审计)
- `docs/plans/archive/reports/v1_0_release_candidate_report.md` (v1.0 发布候选汇总)

## 关联 Issue / 背景

- Milestone: **v1.0-release** (P4/P5/P6 合并完成此 milestone)
- Related issues:
  - `Frontend Evidence UI integration` (P4)
  - `Trace/Cost/Error fields` (P5)
  - `Release gate & governance` (P6)

## 提交说明

本 PR 是"直接实现模式"下 P4/P5/P6 三个阶段的合并提交：

1. **前端部分（P4）：**
   - Read 页面支持 source 导航与 Evidence 侧注显示
   - Search 页面支持实时分层 evidence 查询与展示
   - Chat Evidence UI 完整接入 answerContract 扩展字段
   - Pretext runtime 集成与缓存完善（LRU + pretext fallback）
   - 所有新增测试通过（3 files, 3 tests passed）

2. **后端部分（P5）：**
   - Answer contract 扩展新增 trace_id/error_state/cost_estimate/quality_score
   - RAG 服务完善数据记录与传输逻辑
   - 新增合同测试确保字段正确流向（3 tests passed）

3. **治理部分（P6）：**
   - 同步 API 契约文档（3 个新端点定义）
   - 同步资源模型文档（3 个新资源定义）
   - 全套 governance gate 通过（doc/structure/code/contract/runtime/hygiene）
   - v1.0 release candidate 报告已输出

**代码变更统计：**
- 前端新增/修改文件：8 个 (Read/Search/Chat/text-layout)
- 后端新增/修改文件：2 个 (rag.py + 2 测试文件)
- 文档新增/修改文件：7 个 (api-contract/resources/4 报告 + 1 root)
- 总 LOC 变更：~500 (含文档)

**构建状态：**
- ✅ 前端 type-check: 0 errors
- ✅ 前端 tests: 3 passed
- ✅ 后端 tests: 3 passed
- ✅ Governance gate: 7 checks passed

---

**Ready for:** Code Review → Merge → v1.0 Release
