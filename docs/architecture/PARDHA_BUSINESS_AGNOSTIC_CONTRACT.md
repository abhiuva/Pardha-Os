# Pardha Business-Agnostic Contract

| | |
|---|---|
| Jira | PE0OM-93 (Wave 0), epic PE0OM-92 |
| Status | **PROPOSED, awaiting Product Owner sign-off.** Nothing here overrides Architecture B or an earlier PO decision until signed off. |
| Baseline | `develop` @ `97890a1`, 2026-11-17 |
| Inputs | Pardha AI OS MVP Master Plan v1.0 (2026-11-17); `CLAUDE.md` §4 Architecture B (locked); PE0OM-34..39, PE0OM-56 (75–79), PE0OM-33, PE0OM-32 |

This document maps the product-agnostic MVP plan onto the approved architecture. Section 2 lists every point where
the plan would change an approved decision; each needs explicit PO sign-off and is **not** adopted by this document.

## 1. Layer mapping: Architecture B ↔ MVP plan ↔ existing code

| Architecture B layer (locked) | MVP plan term | Existing modules (reuse) | Jira |
|---|---|---|---|
| Founder Conversational Layer | Founder/Operator Console, CEO conversation, voice | `dashboard/src`, `app/conversations` (voice sessions) | PE0OM-33, 50, 60 (Codex lane) |
| Authenticated Conversation Gateway | Authenticated principal → tenant/business scope | `app/auth`, `app/enterprise`, `app/business`, `app/conversations` | PE0OM-76, 77, 55 |
| OpenAI Chief of Staff | CEO Orchestrator / Plan Engine / Task Delegation | `app/chief_of_staff`, `app/planning`, `app/ceo_agent` (uncommitted, PE0OM-33/73) | PE0OM-44, 58, 73 |
| Registered Specialist Agent Runtime | Agent registry, org chart, agent instances | `app/agents`, `app/capabilities`, `app/mcp`, `app/kernel`, `specialists` table | PE0OM-45, 61–66 (design gates), 84–89, 94 |
| Central Policy / RBAC / HITL | Policy-enforced capability gateway, approval gate, budgets | `app/capabilities/policy.py` (PE0OM-75), `app/planning` approvals | PE0OM-75, 77, 78, 59 |
| Durable Verified Executor | Durable execution control plane: claims, leases, retries, idempotency | `app/runtime`, `app/planning`, write guard (PE0OM-75) | PE0OM-78, 58 |
| Business Connectors and Memory | Business packages, connectors, scoped memory | `app/jira`, `app/hubspot`, `app/sales`, `app/marketing`, `app/knowledge`, `app/memory` | PE0OM-46, 47, 48, 94, 95, 96 |
| (cross-cutting) Model routing | Reasoning Gateway (truthful fallback, metering) | `app/reasoning`, `app/ai` | PE0OM-32, 43, 57 |

The plan fits inside Architecture B without adding a layer. Its new concepts (business packages, agent instances,
task leases, budgets) live inside existing layers.

## 2. Divergences that need PO sign-off (not adopted)

| # | MVP plan says | Approved position today | Proposal |
|---|---|---|---|
| A1 | "CEO Orchestrator" plans and delegates | The **OpenAI Chief of Staff** plans and delegates | Treat "CEO" as the founder-facing name of the Chief of Staff. No second orchestrator. |
| A2 | Reasoning Gateway "selects configured model" (provider-neutral) | Chief of Staff is **OpenAI** (model ID configurable) | Keep it: the Chief of Staff requests `provider=openai` through the gateway. The gateway stays provider-neutral for other callers. See §3. |
| A3 | Sales Scout/Writer/Handler/Analyst, PM and CTO are "P0 active" | Specialists are **design gates** (PE0OM-61..66); no build without an approved spec | No specialist is implemented before its gate is approved. Until then the Chief of Staff may call only existing registered **read** capabilities, labelled deterministic. Sales (PE0OM-96) stays blocked by PE0OM-64. |
| A4 | Approval must come from a **different** principal than the requester | Specific human approval bound to the exact payload | Agent-initiated actions: requester = agent instance, approver = authorized human. Founder-initiated external writes: **PO decision** (second approver or founder self-approval with confirmation). |
| A5 | Tenant + business scoping on every record; multiple business packages | Tenant/project isolation; "never mix projects" | Compatible. Ownership backfill follows the locked rule: quarantine, never auto-assign. |
| A6 | Reversible migrations validated on clean PostgreSQL | No decision; schema today is created from models | Adopt Alembic (new dependency, **PO approval**). |
| A7 | Browser speech recognition, push-to-talk | Jarvis is an unapproved candidate; fallback is React text chat | Compatible if browser API only (no Jarvis import). Codex lane. |
| A8 | Per-agent budgets, soft alert, hard block | Token/cost/time limits; no spend without PO budget approval | Compatible. Budgets enforced in the policy layer before dispatch. |
| A9 | 12–15 working days for Waves 0–3 | Dec 7 sprint plan (PE0OM-34..39) | PO set PE0OM-92 as the current roadmap. Wave 0 depends on PE0OM-75/76/77 (see §6). |

## 3. Chief of Staff vs Reasoning Gateway boundary

| Concern | Reasoning Gateway (`app/reasoning`) | Chief of Staff (`app/chief_of_staff`) |
|---|---|---|
| Purpose | Provider-neutral model call transport | Business-scoped planning, delegation, approval requests, outcome verification |
| Decides | Which provider/model serves a call (config + availability + budget) | What to do next, which registered capability to request |
| Must not | Make permission decisions; execute tools; read business data beyond the prompt it is given | Execute writes directly; treat model output as verified data; approve its own actions |
| Inputs | Prompt, schema, requested provider, budget context | Authenticated `BusinessScope`, founder request, evidence from read capabilities |
| Outputs | Text/structured result + provenance: requested provider, actual provider, model, `fallback_used`, `fallback_reason`, tokens, cost (`null` = unknown), latency | Plan/response + envelope (§7.3); capability requests go through policy |
| Model | Any configured provider; deterministic fallback | **OpenAI** (Architecture B). If unavailable: a degraded response labelled `reasoning_used=false, fallback_used=true`, never presented as Chief of Staff reasoning |

Current state (verified): the gateway's OpenAI provider is configured but intentionally **not enabled** (it raises
"not enabled in this local build"); a second provider abstraction exists in `app/ai`. The Chief of Staff service composes
deterministic agent briefs and summaries. PE0OM-43 (real OpenAI adapter, single honest router) and PE0OM-44 (Chief of
Staff orchestration) close this; no OpenAI spend is authorized yet.

## 4. Proposed decisions (ADRs, pending sign-off)

1. **Extend, replace nothing.** Control-plane concepts are reimplemented inside existing modules. No Paperclip code.
2. **Per-request scope.** Each request resolves `AuthenticatedActor` (session) → `BusinessScope(tenant_id, business_id, role)`
   from server-side membership. Services take scope explicitly. The process-wide "active business" selection is retired;
   a user's last-selected business is a per-user UI preference only. (PE0OM-77)
3. **Background jobs** iterate authorized active businesses with an explicit immutable scope each; no global default. (PE0OM-77)
4. **Foreign ids** → `404` for non-members (no existence oracle); `403` for members lacking the role or policy.
5. **No product names in engine code.** Selection comes from business packages; names only in demo seed data, seeding only when explicitly enabled. (PE0OM-77/94)
6. **Policy in server code.** Capabilities classified `read | draft | write | destructive`; decision = membership ∧ agent grant ∧ process scope ∧ connector grant ∧ risk rule ∧ budget; deny wins. Extends the PE0OM-75 allowlist. (PE0OM-78)
7. **Approvals are persisted requests, never request flags** (§7.4). (PE0OM-78)
8. **Execution is claimed, leased and idempotent.** Postgres: `SELECT … FOR UPDATE SKIP LOCKED` + lease; tests: optimistic `version` compare-and-set. APScheduler only enqueues. An action is `completed` only when the destination confirms it. (PE0OM-78/58)
9. **Truthful metadata.** Unknown usage is `null`/`unknown`, never zero; mock and demo data are labelled.
10. **Routing.** Existing unversioned routes stay. New business-scoped routes use `/businesses/{business_id}/…`. No `/api/v1`.
11. **Migrations.** Alembic baseline + one reversible revision per schema PR, checked up/down on disposable Postgres (A6).

## 5. Existing tables → proposed entities (no duplicate persistence)

| Proposed entity | Proposal | Existing basis |
|---|---|---|
| `business_packages` | **New**: versioned config + digest per business | `businesses` has only name/type/description |
| `agent_instances` | **New**, business-scoped, references a role template | `agents` (unscoped, minimal) kept as legacy; `specialists` are role templates |
| `business_process_definitions` | **New**, versioned, owned by a package | none |
| `agent_tasks` | **Extend `tasks`** (tenant, goal/plan/node links, parent, assignee instance, priority, dependencies, version, idempotency key) | `tasks` is business-scoped with assignee and status |
| claims / leases | **Extend `runtime_queue_items`** (tenant, claimed_by, lease_expires_at, attempt, max_attempts, next_attempt_at, idempotency key unique per business, version) | has priority, retry_count, delay, status |
| `agent_runs` | **New**, one row per attempt (trace, provider/model, fallback, tokens, cost nullable, evidence, error) | `runtime_executions` remains the aggregate; `capability_executions` gains `run_id` |
| `approval_requests` | **New** unified table (payload, payload digest, risk, state, version, expiry, requester, decider) | `plan_approvals`, `meta_ad_approvals`, `software_factory_approvals` stay and gain a link; consolidate later |
| `agent_activity` | **Reuse `audit_logs`** (+ trace/run/task ids), insert-only | `audit_logs` already holds tenant, business, user, approval, execution, outcome |
| tenant scoping | Add `tenant_id` to business-scoped tables as each PR touches them, backfilled via `businesses` | most domain tables carry only `business_id` |

## 6. Delivery order and existing-issue crosswalk

Dependency chain (Jira "Blocks" links respected):
`PE0OM-75 (PR #6, in review) → 76 → 77 → 94 (W1) → 78 → 79`, with `PE0OM-93` (this document) blocking `PE0OM-94`,
and `PE0OM-95` + `PE0OM-64` design gate + `PE0OM-78` blocking `PE0OM-96` (sales, no send).

| MVP plan item | Existing issue(s) | Note |
|---|---|---|
| Authenticated principal, public allowlist | PE0OM-76 | Design attached to PE0OM-76; blocked by PE0OM-75 |
| Tenant/business isolation, Founder/Viewer, retire shared business state | PE0OM-77 | Wave 0 exit gate depends on it |
| Server approvals, idempotency, retries, executor | PE0OM-78 (also overlaps PE0OM-49, 59) | PE0OM-49 overlaps 76–78; PO may close it as duplicate |
| Security suite, CI | PE0OM-79, 74 | |
| Business packages, agent context | PE0OM-94 | Blocked by 93 and 77 |
| CEO orchestration | PE0OM-44, 58, 73; UI PE0OM-33 | A1 |
| Truthful model routing | PE0OM-32, 43, 57, 68 | |
| Conversation gateway | PE0OM-55 | Blocked by 76 |
| Specialists (PM, Eng, Mkt, Sales, Ops, QA) | Gates 61–66 → builds 84–89 | A3 |
| Harvey MIT sales | PE0OM-95 (licence gate) → 96 | Also blocked by PE0OM-64 |
| Memory | PE0OM-46 | |
| Jira/GitHub writes | PE0OM-47, 48 | Approval-bound, via PE0OM-78 |
| Voice | PE0OM-50 (Codex), 54 | A7 |
| Dual-business acceptance and demo | PE0OM-97, 90, 91 | |
| **Gap:** second business package + UVA workflow (backend) | none | Needs a Claude story in Wave 3 |
| **Clarify:** PE0OM-82 "atomic two-agent story claiming" | PE0OM-82 | Dev automation (Jira), not runtime task leases |

## 7. One-page API contract (proposed; frozen after sign-off)

### 7.1 Error contract
`401` no/invalid/expired session · `404` business or record not visible to the actor · `403` role or policy denial ·
`409` state or version conflict · `422` validation. Error bodies are generic; no tokens or internals.

### 7.2 Routes (all require a session and business membership unless stated)

| Method | Path | Role | Story |
|---|---|---|---|
| GET | `/` | public | existing |
| POST | `/auth/login` | public | existing |
| GET | `/businesses` | any | lists only the actor's businesses (77) |
| POST | `/businesses` | founder | creates in the actor's tenant (77) |
| POST | `/businesses/{id}/packages/apply` | founder | validate + store version, `dry_run` default true (94) |
| GET | `/businesses/{id}/agents` | viewer | roster (94) |
| POST | `/businesses/{id}/ceo/commands` | founder | `Idempotency-Key` header; plan/response + envelope (44) |
| POST | `/businesses/{id}/goals` | founder | (94/44) |
| POST | `/businesses/{id}/plans/{plan_id}/submit-review` | founder | creates an approval request (78) |
| GET | `/businesses/{id}/tasks` | viewer | goal-scoped task graph (78) |
| GET | `/businesses/{id}/runs` | viewer | states, cost (`null` = unknown), errors (78) |
| GET | `/businesses/{id}/approvals` | viewer | HITL outbox (78) |
| POST | `/approvals/{approval_id}/decision` | authorized human ≠ requester | `{decision, comment, expected_version}`; business re-derived from the record (78) |
| POST | `/businesses/{id}/sales/qualify` · `/sales/draft` | founder | draft only (96) |
| GET | `/businesses/{id}/sales/outbox` | viewer | staged, unsent (96) |
| GET | `/businesses/{id}/briefs/latest` | viewer | evidence-backed (44) |

Existing endpoints keep their shapes; additions are additive. The dashboard keeps working through compatibility adapters until PE0OM-33 switches over.

### 7.3 Response envelope (new and changed endpoints)
`tenant_id, business_id, trace_id, source_ids[], data_freshness, demo_data, agents_invoked[], reasoning_provider,
reasoning_model, reasoning_used, fallback_used, permissions_decision{decision, reason}, approval_state, execution_status`.
Fields that do not apply are omitted, never faked.

### 7.4 Approval contract
- `payload_digest = sha256(canonical_json({tenant_id, business_id, action_type, target, payload, approval_version}))`, canonical = UTF-8, sorted keys, compact separators.
- States `pending → approved | rejected | expired | revoked`; `approved → consumed` (single use). Decisions carry `expected_version` (`409` on mismatch).
- At execution: recheck membership, target, budget, idempotency key and digest; mismatch → deny + audit.
- `approved` ≠ `sent` ≠ `completed`; approval history and execution history are separate. No request field can grant approval.

### 7.5 Business package v1
Schema as in the master plan (`package_version, business_key, business_type, products, goals, agents, processes[], connectors, policies`).
Validation rejects `auto_send: true` and `default_external_writes: allow` while out of MVP scope. Engine code never branches on `business_key`.

## 8. File ownership (Claude / Codex)

| Area | Owner | Notes |
|---|---|---|
| `pardha-core/app/**`, schema and migrations | Claude | backend and contracts |
| `docs/architecture/**` (this contract) | Claude | changes only by reviewed PR |
| `pardha-core/tests/test_pe0om7*_*.py`, `tests/pardha_auth_support.py` | Claude | story tests and shared auth fixture |
| `dashboard/**` (CEO Founder Console, PE0OM-33) | Codex | includes the authenticated fetch wrapper the dashboard needs for PE0OM-76 |
| `pardha-core/tests/test_adversarial_*.py`, E2E/Playwright | Codex | independent negative tests |
| QA reports and reviews | Codex | Claude never self-certifies |

Separate worktrees and branches; never both tools on one file at once; shared contract changes go through a PR to this document.

## 9. Third-party code policy

- **Harvey:** only tag `v0.3.0` = commit `e2632eb20ee2d4fb6fe04ae715a52f578acf9a37` (MIT, © 2026 Ethan Rogers). Any reused file is listed in
  `THIRD_PARTY_NOTICES.md` with source path, commit, licence text and modifications, and is reviewed in PE0OM-95 before use.
  Its SQLite store, dashboard, scraping and SMTP transport are not imported.
- **Sellbird ≥ v0.4.0:** AGPL-3.0. **No source may be copied.** Behaviour may be studied only to write an independent implementation.
- **Paperclip** (`paperclipai/paperclip`, MIT): architecture reference only; no code imported.
- **Jarvis:** unchanged; unapproved candidate under `CLAUDE.md` §4.

## 10. Baseline and Wave 0 exit gate

Baseline: `develop` @ `97890a1`, backend **155/155** tests pass on a fresh disposable SQLite database with scheduler and
connectors disabled; with PR #6 applied, 193/193. Frontend build passes.

Wave 0 exit gate (PE0OM-92) and current status:

| Gate item | Status | Closed by |
|---|---|---|
| Two parallel sessions cannot affect each other's business | NOT MET | PE0OM-76 + 77 |
| No public route bypasses ownership | NOT MET | PE0OM-76 (route inventory test) + 77 |
| Baseline tests/build documented | MET (above) | this document |
| Licence inventory approved | PENDING PO | §9 sign-off |
| ADR signed off | PENDING PO | §2, §4 |
