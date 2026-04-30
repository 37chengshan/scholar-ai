# v3.0C Claim Locator Contract

日期：2026-04-28
状态：contract

## 1. 目的

定义 Phase C 唯一 claim/evidence 定位契约，供 Chat、Review、Read 三端共享。

## 2. ClaimUnit（P0）

```json
{
  "claim_id": "string",
  "claim_text": "string",
  "claim_type": "fact|comparison|numeric|limitation|interpretation",
  "surface_context": "string",
  "source_sentence_index": 0,
  "support_status": "supported|weakly_supported|unsupported",
  "support_score": 0.0,
  "supporting_evidence_ids": ["string"],
  "repairable": true,
  "repair_hint": "string"
}
```

约束：

1. claim_id 在一次 answer/review 输出内唯一。
2. support_status 只允许三个值。
3. supporting_evidence_ids 必须引用 EvidenceAnchor.evidence_id。

## 3. EvidenceAnchor（P0）

```json
{
  "evidence_id": "string",
  "paper_id": "string",
  "source_chunk_id": "string",
  "quote_text": "string",
  "source_offset_start": 0,
  "source_offset_end": 0,
  "page_num": 1,
  "section_path": "string",
  "content_type": "text|table|figure|caption|formula|page",
  "citation_jump_url": "/read/{paper_id}?..."
}
```

约束：

1. quote_text 不能为空（P0）。
2. source_offset_start/source_offset_end 缺失时，必须显式设 null，且在 verifier 标注为弱证据。
3. citation_jump_url 是统一跳转字段，read_url 仅兼容别名。

## 4. ClaimVerificationResult（P0）

```json
{
  "claim_id": "string",
  "support_status": "supported|weakly_supported|unsupported",
  "support_score": 0.0,
  "evidence_ids": ["string"],
  "reason": "string",
  "verification_mode": "claim_level"
}
```

## 5. Chat/Review 回写契约

- AnswerContract.claims[] 使用 ClaimUnit 精简映射（保留向后兼容字段）。
- AnswerContract.evidence_blocks[] 承载 EvidenceAnchor。
- AnswerContract.claim_verification.results[] 承载 ClaimVerificationResult。

## 6. 兼容策略

- 历史状态 partially_supported 映射为 weakly_supported。
- 历史字段 source_id/chunk_id 兼容读，统一写 source_chunk_id。
- 历史字段 text_preview/snippet 兼容读，统一写 quote_text。

## 7. 非目标

- 本契约不定义 bbox 的标准形状（P1）。
- 本契约不包含 OCR pipeline 细节。
