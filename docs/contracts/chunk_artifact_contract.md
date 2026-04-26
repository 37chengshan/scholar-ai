# ChunkArtifact Contract

## Contract

- artifact_type: chunk_artifact
- contract_version: v1
- parse_id: ParseArtifact parse_id
- paper_id: paper identifier
- stage: one of `raw | rule | llm`
- source_chunk_id: stable cross-stage source identity
- chunk_id: stage-specific identity (`{source_chunk_id}:{stage}`)
- parent_source_chunk_id: null for raw; set to source_chunk_id for derived stages
- content_type: currently text
- content_data: chunk text payload
- section_path: original section path
- normalized_section_path: normalized path string
- section_leaf: normalized leaf section
- page_num: nullable page index
- char_start: nullable char start
- char_end: nullable char end
- anchor_text: nullable anchor/snippet
- warnings: artifact warnings

## Stable Identity

`source_chunk_id = sha256(parse_id|content_type|page_num|normalized_section_path|char_span|anchor[:120])`

- char span contributes only when both `char_start` and `char_end` are present.
- when char span is unavailable, it must remain null and warning `missing_char_span` should be emitted.

## Stage Alignment

- raw/rule/llm artifacts must preserve identical `source_chunk_id` sets.
- derived stage artifacts (`rule`, `llm`) must set `parent_source_chunk_id = source_chunk_id`.
- stage-specific `chunk_id` is derived only by appending stage suffix.
