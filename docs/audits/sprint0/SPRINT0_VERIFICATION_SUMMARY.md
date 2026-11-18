# Sprint 0 Verification Summary (PE0OM-40, PE0OM-41)

Prepared: 2026-11-16 · Public-safe summary. Detailed security findings are kept in private project
documentation (Jira PE0OM-41) and are deliberately not published in this public repository.

This is Claude's development verification. Independent Codex QA is tracked separately and isn't
claimed here.

## 1. Baseline

| Item | Value |
|---|---|
| Source commit (original `pardha-core`) | `422857fb3388cda58ae3e47bd346944590045612` |
| Monorepo PR #1 head | `13c21955d45841a833d455dfca8b687d04cfdd54` |
| `main` after PR #1 (merge commit) | `a924fcc623df34426545517b73795447be9904df` |
| `develop` after sync PR #2 (merge commit) | `08e4bf51ae1d87a42ee12a78ddf5c2f36ce5b23a` (later: PR #3 `4c93f5b`, PR #4 `97890a1`) |
| `pardha-core/` tree hash | `7c792c1c21fb76b5eaef8db1eb8c196d3519aade` (identical to the source commit's tree) |

## 2. Monorepo publication (PE0OM-40)

| Check | Result |
|---|---|
| Imported with a merge commit (subtree, not squashed); all 11 original commits kept | PASS |
| `pardha-core/` tree identical to the source commit | PASS |
| 279 files, all regular files; no gitlink; no `.gitmodules` | PASS |
| `git fsck --full`, `git diff --check` | PASS |
| The PR #1 merge added no content beyond the reviewed PR (identical trees) | PASS |
| `develop` synced through a merge-commit PR; tree identical to `main` | PASS |
| Clean clone contains `app/`, `dashboard/`, `migrations/`, `tests/`, `scripts/` | PASS |

Process note: Codex completed independent QA of PR #1 before the merge (verdict: PASS WITH
CONDITIONS for the repository conversion; the conditions are the pre-existing baseline gaps in
section 6). Its report wasn't recorded on the PR or in Jira before merging, which is logged as a
historical process deviation. A retrospective re-verification of the merged result found no differences.

## 3. Build, run and tests

Setup and commands: [`docs/DEVELOPER_SETUP.md`](../../DEVELOPER_SETUP.md). Every run used a disposable
SQLite database, mock connectors, Ollama disabled, deterministic reasoning and no credentials.

| Check | Result |
|---|---|
| Backend install (Python 3.14.6) | PASS. Versions resolved on 2026-11-16 are recorded in [`evidence/pip-freeze-py314.txt`](evidence/pip-freeze-py314.txt), a historical snapshot, not a lock file. `requirements.txt` is unpinned, so a later install may resolve newer versions. |
| Backend boot, `GET /` | 200 in about 2.6 s |
| Dashboard `npm ci && npm run build` | PASS |
| Unit tests | Baseline: 155 run, 1 error (a stale mock target in the scheduler test, not a product regression). Fixed by **PE0OM-72** (PR #3, merged after Codex PASS): 155 run, OK |

## 4. Secret scanning

- **Gitleaks 8.30.1:** no leaks in the full history, the working tree, or the original pre-monorepo
  repositories.
- **detect-secrets 1.5.0:** keyword hits on HEAD were all triaged as false positives (configuration
  labels, documented test-only passwords, a dummy test key). Nothing additional in history.
- No tracked environment, database, key or credential files.

## 5. Dependencies

- Python (`pip-audit`): no known vulnerabilities. `requirements.txt` is unpinned.
- Dashboard (`npm audit --package-lock-only`, re-run **2026-11-18 03:34 UTC**, Node 23.11.0, npm 10.9.2,
  unchanged lockfile from `056035d`): **17 advisories (15 high, 2 moderate, 0 critical)**, all in build
  and dev-server tooling (Vite, Tailwind CSS, PostCSS and their file-matching dependencies). The production
  dependencies (`react`, `react-dom`; `--omit=dev`) have **0** advisories. The earlier figure of
  7 advisories (5 high, 2 moderate) was undated; the increase comes from newly published advisories, not
  from a dependency change. Several Vite advisories concern the dev server, which must stay bound to
  `127.0.0.1`. Evidence: [`evidence/npm-audit-2026-11-18.txt`](evidence/npm-audit-2026-11-18.txt).
- Both tracked in **PE0OM-74** (CI, dependency security and isolated testing).

## 6. Audit conclusions (category level)

The Sprint 0 audit concluded that Pardha is suitable today only as a **controlled, local,
founder-led prototype** using deterministic responses and mock connectors. It must not be
deployed or exposed publicly until the security foundation is in place.

| Area | Status | Tracked in |
|---|---|---|
| Authentication and project-level authorization across the API | Not yet enforced | PE0OM-56 (highest priority) |
| Central human-approval (HITL) gate for all external writes | Not yet universal | PE0OM-56 |
| Live model reasoning (OpenAI Chief of Staff) | Not yet implemented; current answers are deterministic and labelled as such | PE0OM-43 |
| Versioned contracts and model observability | Not yet implemented | PE0OM-57 |
| Authenticated conversation gateway and Chief of Staff handoff | Not yet implemented | PE0OM-55 |
| CI, dependency hygiene, test-database isolation | Not yet in place | PE0OM-74 |
| Uncommitted CEO Agent prototype (not in this repo) | Preserved; to be reworked as a secure read-only capability | PE0OM-73 |

## 7. Reports

See [SPRINT0_AUDIT_INDEX.md](SPRINT0_AUDIT_INDEX.md). Reports 02–06 and 08–12 are published here;
reports with detailed security findings are private.
