# Pardha Repository Publishing Audit

## Finding

The parent `Pardha-Os` repository tracked `pardha-core` as a Git gitlink
(mode `160000`) but did not contain a `.gitmodules` entry. GitHub therefore
displayed only a commit pointer and had no repository URL from which to load
the backend and frontend source.

## Resolution

`pardha-core` is now included as a normal directory in this repository using a
non-squashed Git subtree import. This preserves the existing `pardha-core`
commit history while making the complete committed backend, dashboard, tests,
migrations, and documentation directly visible in the monorepo.

The import used committed `pardha-core` revision:

```text
422857fb3388cda58ae3e47bd346944590045612
```

No application logic was changed as part of the repository conversion.

## Repository Layout

```text
Pardha-Os/
|-- knowledge/          Parent-level DP360 knowledge assets
|-- pardha-core/
|   |-- app/            FastAPI backend
|   |-- dashboard/      React and Vite frontend
|   |-- migrations/     Database migrations
|   |-- scripts/        Maintenance and validation scripts
|   |-- tests/          Backend and integration tests
|   `-- requirements.txt
`-- REPOSITORY_AUDIT.md
```

## Secret Audit

The tracked parent and `pardha-core` histories were checked for common private
key blocks and recognizable AWS, GitHub, OpenAI, and Google credential token
formats. No matches were found. Files matching credential-related terms were
reviewed and use environment variables, password hashing, or request schema
fields rather than embedded live credentials.

Environment files, local databases, virtual environments, Node dependencies,
build output, and logs are excluded by the existing ignore rules.

Production deployments must provide `PARDHA_JWT_SECRET`; the backend contains a
clearly labeled development-only fallback value. This audit does not change
application behavior.

## Ongoing Maintenance

Develop directly in the monorepo under `pardha-core/`. If the standalone local
repository must remain temporarily during migration, use `git subtree pull`
without `--squash` so future imported commits retain ancestry. Avoid restoring
the gitlink unless a valid `.gitmodules` URL and a deliberate submodule workflow
are introduced.
