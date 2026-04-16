# apps/api (Logical Mapping)

Current implementation lives in backend-python.

Rules:
- API changes must update docs/architecture/api-contract.md.
- Resource lifecycle changes must update docs/domain/resources.md.
- apps/api is logical mapping only in current milestone.
- Do not place business source files under apps/api (py/ts/tsx/js/jsx).
- backend-python is the only active backend source-of-truth path.
