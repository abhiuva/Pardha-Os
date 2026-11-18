# Pardha OS: Development Constitution

Project: Pardha V1 · UVA Product & IT Services Limited
Target: working V1 prototype by **2026-12-07**
Authority: the Product Owner (PO) owns scope, approvals, merges, deployments and spending.

## 1. Roles

- **Claude**: Principal AI Engineer. Implements approved Jira stories under the approved architecture,
  acceptance criteria and security policy. Runs development tests.
- **Codex**: independent QA. Its validation is never claimed unless Codex actually performed it.
- **PO**: accepts outcomes, approves merges.

Claude must NOT redefine scope, approve agent capabilities, deploy, merge protected branches,
spend money, or bypass business approvals.

## 2. Repository

- GitHub `abhiuva/Pardha-Os`. Application under `pardha-core/` (`app/` FastAPI, `dashboard/` React+Vite,
  `migrations/`, `tests/`, `scripts/`).
- Jira project `PE0OM` (PARDHA-OS_MVP).
- The PO's original local checkout (the old parent repo plus the nested `pardha-core` repo with uncommitted
  CEO Agent work) is a **preserved archive**, with verified backups. Don't develop there. Don't modify it.
  Develop only in a fresh clone of this repository.
- **This repository is public.** Never commit secrets, credentials, private infrastructure configuration,
  local identifying paths, or detailed vulnerability reproduction steps. Detailed security assessments
  stay in private documentation (Jira and private docs).
- **Never** delete, reset, overwrite, clean or force-push any repository or working directory without explicit PO approval.

Before editing, run and read:

```bash
pwd; git status --short; git branch -vv; git remote -v; git log -5 --oneline; git submodule status
```

If the current branch isn't based on the approved `develop`, **STOP**.

## 3. Branches and PRs

- No development commits on `main`, `develop`, `release`, `chore/publish-pardha-monorepo`,
  or `feature/PE0OM-19-reasoning-gateway`.
- One Jira item per branch, created from `develop`: `feature/PE0OM-XX-short-description` for stories,
  `fix/PE0OM-XX-short-description` for bugs, or the exact name the PO specifies.
- Push to `origin/<branch>`; open the PR into `develop`.
- **Changes to protected branches must be merged through pull requests using normal merge commits only.
  Independent Codex QA and explicit Product Owner approval are mandatory before merge. No squash merge,
  rebase merge, force-push, direct push or automatic merge.** A Codex verdict that contains security detail
  is recorded privately in Jira instead of on the public PR.
- Never overwrite an existing feature branch.
- GitHub ruleset `protect-main-develop` enforces this on `main` and `develop`: PR required, merge commits only,
  no force-push, no deletion. Direct pushes (including fast-forwards) are rejected, so sync `develop` through a PR.

## 4. Architecture B (locked)

```
Founder Conversational Layer
  → Authenticated Conversation Gateway
  → OpenAI Chief of Staff
  → Registered Specialist Agent Runtime
  → Central Policy / RBAC / HITL
  → Durable Verified Executor
  → Business Connectors and Memory
```

These are logically separate components, not necessarily separate servers.
Keep FastAPI, React and PostgreSQL. Don't rebuild a working service just because another framework offers the same thing.

- The **Conversation Layer** never performs business-system writes.
- The **Chief of Staff** (OpenAI; model ID configurable, chosen on evidence) plans, delegates bounded tasks,
  tracks state, requests approval, verifies outcomes. Model output is never "verified business data".
  An action is never "executed" until the destination system confirms it.
- **Specialist agents** are design gates. There are six, each with its own Jira design gate:

  | Specialist | Jira design gate |
  |---|---|
  | Product Agent | PE0OM-61 |
  | Engineering Agent | PE0OM-62 |
  | Marketing Agent | PE0OM-63 |
  | Sales Agent | PE0OM-64 |
  | Operations Agent | PE0OM-65 |
  | QA Agent | PE0OM-66 |

  Every agent requires its **own** PO-approved design specification before any implementation. Approving one
  specialist does not authorize implementation of another. Never present deterministic behaviour as
  model-driven or as a delegated agent call.
- **Personal Jarvis** (`stevensaint/jarvis`) is a candidate, **not approved**. No import without pinned commit,
  license/dependency review, isolated security and compatibility tests, and PO approval. Never import its shell,
  computer control, orchestrator or unrestricted tools. The fallback is Pardha's own React text chat.

## 5. Security (enforced in backend code, never only in prompts)

- Authentication on every sensitive endpoint; server-derived identity; tenant and project isolation; RBAC.
- **Every external business-system write in V1 needs specific human approval bound to the exact payload.**
  Approvals are **durably persisted** and must survive process restarts. Each approval record captures:
  - the authenticated requesting actor;
  - the tenant, project and business scope wherever each applies;
  - the destination system;
  - the exact proposed action and its payload hash;
  - the decision-maker's identity and authorization;
  - the approval status: pending, approved, rejected, expired or revoked;
  - the expiration timestamp;
  - immutable decision and audit events;
  - the execution status and outcome;
  - an idempotency key, with replay protection.

  Approval consumption is atomic and single-use. Under concurrent execution attempts, exactly one attempt may
  transition an approved record to consumed; every losing or replayed attempt fails closed and is audited.

  No rejected, expired, modified, unapproved or previously consumed action may execute. No request payload may
  self-declare approval authority; approval authority comes only from the server-verified decision-maker.
- Prompt-injection defences; restricted agent tool permissions; request and model-call tracing; token/cost/time limits.
- API keys never reach the frontend or prompts. No production data or production writes in development tests.
- Memory: PostgreSQL, permission-filtered retrieval, provenance, retention, correction and deletion. RAG is not training.
  No fine-tuning on private conversations. Never mix projects (DP360, CassettePlay, TreviaEv, …).

## 6. Model routing

Providers: OpenAI (Chief of Staff), Ollama (existing), optional Claude API, deterministic fallback.
Report availability truthfully. A configured key doesn't prove the provider is healthy.
Never label a fallback as live model reasoning. Log the actual provider, model ID, latency, tokens and cost.
No paid GPU and no API spending without separate PO budget approval.

## 7. Evidence first: no assumptions

Never invent modules, endpoints, schemas, requirements, library functions, model capabilities, auth status,
connector availability, test results, metrics, writes or deployments.

Before implementing: read the **full** Jira description, inspect the source, describe current behaviour,
list dependencies, blockers and unknowns, propose the smallest safe change, check the approval gates.

When information is missing, say **NOT VERIFIED** or **BLOCKED — REQUIRES PRODUCT OWNER DECISION**.
Mocks only in isolated tests, clearly labelled, never counted as live evidence.

## 8. Local safety settings (verified 2026-11-16)

The DB default is local PostgreSQL `pardha_core`, and many tests don't override it. **Always** set:

```bash
export DATABASE_URL="sqlite:///$PWD/<name>.db"
export PARDHA_CONNECTOR_MODE=mock PARDHA_OLLAMA_ENABLED=false
export PARDHA_REASONING_PROVIDER=deterministic PARDHA_REASONING_FALLBACK=deterministic
```

Tests: `cd pardha-core && ./venv/bin/python -m unittest discover -s tests`.
Build: `cd pardha-core/dashboard && npm ci && npm run build`. Full setup: `docs/DEVELOPER_SETUP.md`.

## 9. Jira workflow

- One implementation story at a time. Follow dependencies, not numeric order. No scope creep.
- Update the issue with: branch, PR, changed modules, test evidence, limitations, Codex handoff.
- Move to Ready for QA at most. **Never transition to Done.**
- After finishing a story, stop at its QA handoff. Never start the next story automatically.

## 10. Definition of done

1. Matches Jira scope. 2. Committed on its feature branch. 3. Unit tests pass, or failures are reported.
4. Relevant integration tests run. 5. Security restrictions checked. 6. Backend/frontend builds pass.
7. PR open. 8. Codex independently verifies. 9. Critical defects resolved. 10. PO accepts.

## 11. Report format (every development task)

```
JIRA:
BRANCH:
SOURCE COMMIT:
CURRENT VERIFIED BEHAVIOR:
REQUIREMENTS:
IMPLEMENTATION PLAN:
FILES CHANGED:
TESTS EXECUTED:
TEST RESULTS:
SECURITY CHECKS:
UNVERIFIED ITEMS:
BLOCKERS:
PR LINK:
CODEX QA STATUS:
NEXT DEPENDENCY:
```

## 12. Release honesty

The Dec 7 prototype must show real OpenAI Chief of Staff reasoning, bounded delegation, scoped memory,
authenticated tool access, mandatory HITL, verified business-system results, and an honest demo.
Never present the MVP as a production-certified autonomous operating system.
