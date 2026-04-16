# ADR 0001: Product Work Happens Under `scholar-ai/`

## Status

Accepted

## Context

The workspace currently mixes product code, model assets, runtime output, historical docs, and orchestration state at multiple levels. This makes it easy for contributors and agents to place files in inconsistent locations and hard to review cleanup changes safely.

## Decision

- `scholar-ai/` is the canonical product workspace.
- The outer repository layer is reserved for model assets and wrapper-level orchestration.
- `docs/` becomes the single documentation root inside `scholar-ai/`.
- Runtime outputs are ignored and must not be committed as loose top-level clutter.
- New feature work must not introduce duplicate `_new`, `legacy`, or parallel doc roots.

## Consequences

- Existing historical material needs staged migration.
- Cleanup work can proceed safely without large feature rewrites.
- Future contributors have a clear boundary for where to place code, docs, and operational artifacts.
