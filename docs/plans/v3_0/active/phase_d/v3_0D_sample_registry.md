# v3.0D Sample Registry

日期：2026-04-29
状态：registry
范围：Phase D 真实论文验证集台账
上游：
- docs/plans/v3_0/active/phase_d/v3_0D_kickoff_freeze.md
- docs/plans/v3_0/active/phase_d/2026-04-29_v3_0D_Real_World_Validation_研究文档.md

## 1. 目的

本文档是 Phase D 所有真实验证 run 使用的唯一样本台账。

- 执行者添加论文样本时，必须填写本文档的标准字段。
- 任何 run 引用 `sample_set` 时，必须能在此处找到对应记录。
- 禁止在本文档之外另建样本清单。

## 2. 样本字段规范

每条样本必须包含以下字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `sample_id` | string | 唯一标识，格式：`D-{序号}` |
| `title` | string | 论文标题（可截断） |
| `source_type` | enum | `arxiv / semantic_scholar / local_pdf / other` |
| `doi_or_url` | string | 原始来源链接或 DOI |
| `discipline` | string | 学科领域，如 `cs.AI / physics / medicine / multi` |
| `document_complexity` | enum | `standard / formula_heavy / scan_pdf / figure_heavy / long_survey` |
| `language_mix` | enum | `en / zh / en-zh / other` |
| `expected_risk` | enum | `low / medium / high / known_failure` |
| `workflow_path` | string | 验证时覆盖的主链段，如 `search->import->chat->review` |
| `observed_failures` | string | 执行后填写，若未执行留空 |
| `run_ids` | string[] | 引用此样本的 run ID |
| `notes` | string | 补充说明 |

## 3. 高风险样本类型清单（必须覆盖）

按研究文档定义，验证集必须覆盖以下八类：

| 类型编号 | 类型名称 | 说明 | 建议最少 case 数 |
|---|---|---|---|
| T1 | 外部导入论文 | 来自 arXiv / Semantic Scholar 的真实导入 | ≥5 |
| T2 | 扫描版 PDF | OCR 质量不稳定，解析可能失败 | ≥3 |
| T3 | 图表密集论文 | figure / table 是主证据来源 | ≥3 |
| T4 | 公式密集论文 | 数学段落与符号解释占高比重 | ≥3 |
| T5 | 长综述论文 | 跨章节综合，全文检索压力高 | ≥3 |
| T6 | 跨学科 KB | 多篇论文来自不同领域，混合证据 | ≥2 KB 组 |
| T7 | 中英文混合 | query / metadata / evidence 混合语言 | ≥3 |
| T8 | 边界失败样本 | 已知可能失败但对 v3.0 重要的场景 | ≥3 |

## 4. 样本台账

> 执行者在运行验证时，按以下格式追加记录。  
> 初始状态为空，执行时填入。

### 4.1 T1 外部导入论文

| sample_id | title | source_type | doi_or_url | discipline | document_complexity | language_mix | expected_risk | workflow_path | observed_failures | run_ids | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| D-001 | Attention Is All You Need | arxiv | https://arxiv.org/abs/1706.03762 | cs.CL | standard | en | medium | search->import->kb->read->chat->notes->compare->review | RW-001: search 30s+ 后返回；import 卡在 KB 选择模态框；evidence sidecar 500；RW-002: search->import->kb->read 实链通过；RW-003: read->notes->chat->review follow-up 实链通过，review honest degraded 到 partial/insufficient_evidence；RW-004: fresh-account search->import->kb->read->notes->chat->review 在真实 Milvus 上通过，compare 未重跑，summary-index insert overflow 被降级处理未阻断主链；RW-005: fresh-account closeout rerun 在真实 Milvus 上通过，导入确认契约与 worker prewarm 生效，但 review 仍为 partial/insufficient_evidence，首轮全链仍约 4.1 分钟 | RW-001, RW-002, RW-003, RW-004, RW-005 | T1 基准样本；RW-002 于 2026-04-29 跑通到 read；RW-003/RW-004 于 2026-04-29 收口到 review；RW-005 为 2026-04-29 closeout 下游重跑，compare 仍未纳入本次执行链 |
| D-002 | _(待填)_ | semantic_scholar | _(待填)_ | _(待填)_ | standard | en | medium | search->import->review | _(执行后填)_ | | T1 Semantic Scholar 路径 |

### 4.2 T2 扫描版 PDF

| sample_id | title | source_type | doi_or_url | discipline | document_complexity | language_mix | expected_risk | workflow_path | observed_failures | run_ids | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| D-010 | The Chemical Basis of Morphogenesis (historical scanned PDF copy) | local_pdf | https://doi.org/10.1098/rstb.1952.0012 | biology | scan_pdf | en | high | import->kb->read->chat->notes->review |  |  | T2 OCR 压力测试，需使用本地扫描件执行 |

### 4.3 T3 图表密集论文

| sample_id | title | source_type | doi_or_url | discipline | document_complexity | language_mix | expected_risk | workflow_path | observed_failures | run_ids | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| D-020 | Segment Anything | arxiv | https://arxiv.org/abs/2304.02643 | cs.CV | figure_heavy | en | high | search->import->kb->read->chat->compare->review |  |  | T3 figure 作为主证据 |

### 4.4 T4 公式密集论文

| sample_id | title | source_type | doi_or_url | discipline | document_complexity | language_mix | expected_risk | workflow_path | observed_failures | run_ids | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| D-030 | Score-Based Generative Modeling through Stochastic Differential Equations | arxiv | https://arxiv.org/abs/2011.13456 | stat.ML | formula_heavy | en | high | search->import->kb->read->chat->notes->review |  |  | T4 公式解析压力 |

### 4.5 T5 长综述论文

| sample_id | title | source_type | doi_or_url | discipline | document_complexity | language_mix | expected_risk | workflow_path | observed_failures | run_ids | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| D-040 | A Survey of Large Language Models | arxiv | https://arxiv.org/abs/2303.18223 | cs.CL | long_survey | en | medium | search->import->kb->read->chat->notes->compare->review |  |  | T5 跨章节检索 |

### 4.6 T6 跨学科 KB

| sample_id | title | source_type | doi_or_url | discipline | document_complexity | language_mix | expected_risk | workflow_path | observed_failures | run_ids | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| D-050 | Cross-discipline KB set: AlphaFold + ClimateBench + Retrieval-Augmented Generation | mixed | https://doi.org/10.1038/s41586-021-03819-2 ; https://arxiv.org/abs/2210.15544 ; https://arxiv.org/abs/2005.11401 | multi | standard | en | high | search->import->kb->read->chat->notes->compare->review |  |  | T6 跨学科 KB 组 1 |

### 4.7 T7 中英文混合

| sample_id | title | source_type | doi_or_url | discipline | document_complexity | language_mix | expected_risk | workflow_path | observed_failures | run_ids | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| D-060 | mT5: A Massively Multilingual Pre-trained Text-to-Text Transformer | arxiv | https://arxiv.org/abs/2010.11934 | cs.CL | standard | en-zh | medium | search->import->kb->chat->notes->review |  |  | T7 中文 query + 英文论文 |

### 4.8 T8 边界失败样本

| sample_id | title | source_type | doi_or_url | discipline | document_complexity | language_mix | expected_risk | workflow_path | observed_failures | run_ids | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| D-070 | LayoutParser: A Unified Toolkit for Deep Learning Based Document Image Analysis | arxiv | https://arxiv.org/abs/2103.15348 | cs.CV | figure_heavy | en | known_failure | search->import->kb->read->chat->review |  |  | T8 已知边界失败 1，布局解析与证据跳转边界样本 |

## 5. 样本规模目标

| 指标 | P0 目标 |
|---|---|
| 总样本数 | 100-300 篇真实论文 |
| 完整 workflow run 数 | ≥20 |
| 八类高风险各至少覆盖 | 见第3节 |
| blocking 样本至少记录 | ≥3 |

## 6. 使用说明

1. 执行者添加新样本时，按类型追加到对应子表。
2. `sample_id` 顺序编号，T1 用 D-001 起，T2 用 D-010 起，以此类推（每类预留 10 个位置）。
3. `observed_failures` 执行前留空，执行后按 `v3_0D_failure_bucket_spec.md` 分桶记录。
4. `run_ids` 可能有多个（同一样本可被多次 run 引用）。
5. 样本记录一旦被 run 引用，禁止删除（只允许更新 `observed_failures` 和 `notes`）。
