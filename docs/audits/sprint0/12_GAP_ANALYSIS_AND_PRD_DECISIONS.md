# Gap Analysis and PRD Decisions

## Gap Matrix

| Feature | Current status | Ready % | Priority | Estimated effort | Primary files/dependencies |
|---|---|---:|---|---|---|
| Unified Chief of Staff | Two overlapping stacks | 50 | P0 | 2-3 weeks | `conversations/`, `chief_of_staff/` |
| Intent/model routing | Keyword + partial gateway | 35 | P0 | 2 weeks | `executive_router.py`, `reasoning/` |
| Global auth/RBAC | Login exists; API-wide enforcement in progress | 25 | P0 | 2-4 weeks | `auth/`, router dependencies, tenant filters |
| HITL enforcement | Records exist; not yet universal | 45 | P0 | 2-3 weeks | planning, runtime, all connectors |
| Durable execution | Local queue/runtime partial | 40 | P0 | 3-5 weeks | `runtime/`, outbox/idempotency |
| Provider support | Ollama + deterministic only | 40 | P1 | 2-3 weeks | OpenAI/Claude adapters, metrics |
| Agent collaboration | Scripted direct calls | 35 | P1 | 2-4 weeks | collaboration/event contracts |
| Business isolation | Query filtering; authorization in progress | 50 | P0 | Included with auth | all repositories/services |
| Memory | Persistent but fragmented/lexical | 45 | P1 | 3 weeks | memory, knowledge, conversation models |
| Connector truthfulness | Mixed real/mock/status | 45 | P0 | 2 weeks | connector status contracts |
| Knowledge ingestion | Broad formats, lexical retrieval | 75 | P1 | 1-2 weeks hardening | `knowledge/` |
| Frontend architecture | Broad UI, monolithic file | 50 | P1 | 3-5 weeks | `dashboard/src/App.jsx` |
| UI validation | No browser test suite | 20 | P0 | 1-2 weeks | Playwright, API mocks/live fixture |
| CI/deployment | Not found | 10 | P0 | 1-2 weeks | GitHub Actions, container/profile docs |
| Observability | Status models, limited real metrics | 35 | P1 | 2-3 weeks | traces, metrics, alerts |
| Colibri integration | None | 0 | P3 | Experiment only | provider adapter, hardware benchmark |

## PRD Decisions Required

1. **Canonical conversation:** Select `app/conversations` and deprecate the older Chief-of-Staff chat path.
2. **Agent definition:** Decide that departments are deterministic tools unless they own an explicit model loop, prompt, memory, tool policy, and evaluation suite.
3. **Approval policy:** Define exact risk classes and which reads/writes require approval; prohibit connector-specific bypasses.
4. **Cloud data policy:** Define which business data may be sent to OpenAI/Anthropic/Gemini and under what tenant consent.
5. **Business context semantics:** Make context per authenticated session/request, never process-global.
6. **Success semantics:** A tool action is successful only after verification, not merely after an API returned 2xx.
7. **Provider SLOs:** Establish accuracy, latency, availability, and cost budgets by task class.
8. **Memory policy:** Define provenance, retention, deletion, supersession, sensitivity, and retrieval rules.
9. **Demo vs production:** Remove ambiguous mock “success” states and show mode prominently.
10. **Source distribution:** Merge the reviewed monorepo recovery PR so the complete source and history are reproducible. *(Historical recommendation, completed 2026-11-16: PR #1 merged into `main` as `a924fcc` and synced to `develop`.)*

## Recommended 90-Day Plan

### Days 1-30: Trust boundary

- Global authentication and tenant/business authorization.
- Central policy/approval wrapper for every external write.
- Correct connector truth states.
- Fix stale test, planning approval state bug, CORS, and startup side effects.
- Add CI and a minimal Playwright founder journey.

### Days 31-60: Intelligence core

- Real OpenAI provider plus structured router with explicit fallback.
- Canonical conversation stack and model-call governance records.
- Durable/idempotent executor with verification.
- Consolidated memory contract and evidence citations.

### Days 61-90: Product hardening

- Split frontend by domain and stabilize loading/error/empty states.
- Production PostgreSQL performance and concurrency tests.
- Connector sandbox certification for Jira and HubSpot.
- Local runtime comparison: Ollama vs llama.cpp vs MLX-LM.
- Pilot readiness review against real founder workflows.

## Release Decision

**Do not market current Pardha as autonomous or enterprise-secure.** It is suitable for a controlled founder-led prototype demonstration with deterministic responses, mock connectors, and explicit disclosure. A paid pilot should begin only after P0 identity, isolation, HITL, connector truth, and execution-verification gaps are closed.
