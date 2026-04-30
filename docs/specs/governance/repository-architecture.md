# Repository Architecture

## Workspace Boundary

- Outer workspace: model assets, top-level orchestration, wrapper README.
- Product workspace: `scholar-ai/`.
- All ongoing feature work, cleanup work, and delivery work should happen inside `scholar-ai/`.

## Target Tree

```text
scholar-ai/
├── AGENTS.md
├── README.md
├── docs/
│   ├── specs/
│   ├── plans/
│   └── README.md
├── apps/web/
│   ├── src/app/
│   └── src/{config,contexts,lib,mocks,services,stores,styles,test,types,utils}/
├── apps/api/
│   ├── app/
│   ├── tests/
│   ├── alembic/
│   └── docs/
├── scripts/
├── tests/
│   └── evals/
├── logs/
├── uploads/
└── .github/
    ├── workflows/
    ├── ISSUE_TEMPLATE/
    └── pull_request_template.md
```

## Canonical Rules

- `docs/` replaces `doc/`.
- `logs/` is the canonical home for archived runtime logs.
- `docs/` root only keeps `README.md`, `specs/`, and `plans/`.
- `docs/specs/` is the canonical home for architecture, governance, design, and reference material.
- `docs/plans/<version>/{active,complete,search,reports}` is the canonical home for plan and delivery artifacts.
- `apps/web/src/app` is the canonical UI feature root.
- `apps/api/app/api/{imports,kb,papers,search}` are the canonical grouped API areas.

## Cleanup Targets

- Remove `doc/` after its remaining material is migrated.
- Stop adding files to top-level runtime clutter such as loose `*.log`, `*.pid`, and one-off report files.
- Retire duplicate backend modules such as `_new` and `legacy` after their routes are fully merged.
- Normalize response schema and field naming before adding new API surfaces.
