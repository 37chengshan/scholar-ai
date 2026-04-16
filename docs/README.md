# ScholarAI Docs Map

`docs/` is the single documentation root for the product workspace.

## Structure

- `architecture/`
  - system topology, API contract, architecture-level references
- `domain/`
  - canonical resource model and lifecycle definitions
- `development/`
  - coding standards, PR workflow, testing strategy, documentation validation
- `engineering/`
  - compatibility entries pointing to `development/`
- `governance/`
  - repository architecture, cleanup plans, governance notes, harness playbook, code boundary baseline
- `adr/`
  - architecture decision records
- `plans/`
  - implementation plans and active execution notes
- `reports/`
  - deliverable reports, audits, and periodic summaries
- `reference/`
  - vendor notes, API references, and imported background material

## Rules

- New project docs go under `docs/`, not `doc/`.
- Core governance docs use these canonical paths:
  - `docs/architecture/system-overview.md`
  - `docs/architecture/api-contract.md`
  - `docs/domain/resources.md`
  - `docs/development/coding-standards.md`
  - `docs/development/documentation-validation.md`
  - `docs/development/pr-process.md`
  - `docs/development/testing-strategy.md`
  - `docs/governance/code-boundary-baseline.md`
  - `docs/governance/harness-engineering-playbook.md`
- Imported reference material goes under `docs/reference/`.
- Deliverable-style reports go under `docs/reports/`.
- Runtime outputs, coverage, and generated logs do not belong here.

## Governance Commands

- `bash scripts/check-doc-governance.sh`
- `bash scripts/check-structure-boundaries.sh`
- `bash scripts/check-code-boundaries.sh`
- `bash scripts/check-governance.sh`
