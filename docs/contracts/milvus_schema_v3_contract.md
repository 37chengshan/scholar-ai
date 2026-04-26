# Milvus Schema v3 Contract

## Purpose

Define first-class retrieval/evidence fields for standardized chunk identity and provenance.

## First-Class Fields

- paper_id
- user_id
- content_type
- page_num
- section
- content_data
- quality_score
- embedding
- chunk_id
- source_chunk_id
- stage
- parent_source_chunk_id
- char_start
- char_end
- anchor_text
- normalized_section_path
- normalized_section_leaf

## Raw Data Boundary

- `raw_data` is supplemental metadata only.
- Critical retrieval identity must not rely exclusively on `raw_data`.
- Runtime/benchmark/citation logic should read first-class fields when available.

## Compatibility Note

Current storage path backfills identity/provenance in `raw_data` while schema migration is staged. This contract defines the target shape and the mandatory field semantics.
