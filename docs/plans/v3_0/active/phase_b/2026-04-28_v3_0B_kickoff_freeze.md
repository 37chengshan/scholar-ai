---
标题：ScholarAI v3.0-B External Search + Import to KB Kickoff Freeze
日期：2026-04-28
状态：freeze
用途：冻结 Phase B kickoff 前必须明确的执行边界
前提：文档层假设 Phase A 已完成并可复用；不等同于仓库当前实现状态
---

# 1. 目的

本文件冻结 `Phase B` 在 kickoff 后不再反复讨论的关键执行边界。

# 2. Freeze-01：Source 范围

P0 阶段正式支持：

1. `arxiv`
2. `semantic_scholar`

P0 阶段不正式支持：

1. 新增更多外部源
2. 同时扩 PubMed / OpenAlex / Crossref 作为前台可选 source

原因：

1. 先把最核心的两源做深做稳
2. 避免 dedupe / availability / download planner 复杂度过早爆炸

# 3. Freeze-02：API Key 边界

1. Semantic Scholar API key 已具备
2. 该 key 只允许保留在后端环境变量
3. 前端不得直接调用第三方接口
4. 所有外部请求必须经后端代理

# 4. Freeze-03：正式入口

唯一正式外部发现入口：

1. `SearchWorkspace.tsx`

不允许：

1. 新造平行 external search 页面
2. 在 KB 页面内再复制一套发现工作区作为主入口

# 5. Freeze-04：正式导入真源

唯一正式 external import 真源：

1. `ImportJob`

不允许：

1. 新造第二套 external import state machine
2. 绕开 ImportJob 直接写 Paper / ProcessingTask 作为主链

# 6. Freeze-05：资源状态语义

P0 必须严格区分：

1. `not_imported`
2. `importing`
3. `imported_metadata_only`
4. `imported_fulltext_ready`

硬规则：

1. 没有 PDF 或未索引完成的论文，只能是 `metadata_only`
2. 只有解析 + chunk + embedding + index 完成后，才允许是 `fulltext_ready`

# 7. Freeze-06：批量策略

P0 批量导入允许，但必须：

1. 尊重 arXiv 节流
2. 尊重 Semantic Scholar 速率限制
3. 通过 ImportJob / queue / cache 控制并发

不允许：

1. 直接高并发猛拉第三方 API

# 8. Freeze-07：Dedupe 顺序

dedupe 顺序固定为：

1. DOI
2. arXiv ID
3. S2 paper ID
4. file SHA256
5. title fuzzy

执行者不得自行调整顺序，除非先更新本文件。

# 9. Freeze-08：导入完成的消费边界

1. `metadata_only`
   - 可见于 KB
   - 可展示 metadata / abstract
   - 不得冒充全文检索可用
2. `fulltext_ready`
   - 可进入 KB / Read / Chat / Notes / Compare 主链

# 10. 执行者如何使用本文件

执行者在 Phase B 实施时：

1. 读完研究文档后，先读本文件
2. 所有未决边界以本文件为准
3. 若后续要改 source 范围、key 边界、导入真源、资源状态语义，先改本文件

# 11. 结论

```txt
Phase B kickoff 之后，
执行者不再需要自己判断“要不要新开页面、要不要让前端直连、要不要把 metadata 当成全文、要不要加更多源”，
这些都以本文件冻结值直接执行。
```
