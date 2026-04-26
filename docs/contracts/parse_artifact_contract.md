# ParseArtifact Contract

## Contract

- artifact_type: parse_artifact
- contract_version: v1
- parse_id: stable id (`sha256(paper_id|source_uri|created_at)` first 32 chars)
- paper_id: paper identifier
- source_uri: source PDF storage key/URI
- parser_name: parser implementation name
- parser_version: parser version if available
- parse_mode: one of `docling_native | docling_ocr | pypdf_fallback`
- quality_level: one of `full | text_only | degraded`
- ocr_used: boolean
- page_count: integer
- markdown: parsed markdown
- items: parsed structural items
- warnings: parser warnings
- supports_tables: boolean
- supports_figures: boolean
- created_at: ISO-8601 UTC timestamp

## Parse Mode Rules

- `docling_native`: standard native parser path.
- `docling_ocr`: OCR-enabled path (force OCR or fallback OCR).
- `pypdf_fallback`: degraded fallback path.

## Quality Rules

- `pypdf_fallback` must map to `text_only`.
- degraded parser failures/timeouts may map to `degraded`.
- otherwise defaults to `full`.

## Safety Constraints

- When parse_mode is `pypdf_fallback`, `supports_tables` and `supports_figures` must be false.
- Benchmark/eval runtime must consume ParseArtifact, not ad-hoc re-parse.
