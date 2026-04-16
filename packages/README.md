# Packages Boundary

This folder reserves long-term shared package space.

Planned package scopes:
- packages/ui
- packages/types
- packages/config
- packages/sdk

## Current Phase Rule

- packages/* does not host active business implementation in current milestone.
- frontend and backend-python remain the only active source paths.

## Migration Criteria

Move code into packages only when all conditions are met:

1. Contract is stable and documented in docs/architecture/api-contract.md.
2. At least two consumers need the same module.
3. Ownership and versioning strategy are defined.
4. CI coverage exists for the extracted package.
5. No parallel implementation remains in original paths.

## Migration Matrix

- packages/types: stable cross-layer DTO/types only.
- packages/sdk: stable API client wrappers after contract convergence.
- packages/ui: reusable UI primitives used by multiple pages/domains.
- packages/config: shared lint/build/tooling configuration only.
