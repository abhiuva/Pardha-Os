# Performance Benchmarks

## Method

These are controlled local measurements, not production benchmarks. The backend used an isolated SQLite database in a temporary directory, deterministic reasoning, Ollama disabled, connector mode `mock`, Jira disabled, and knowledge watcher disabled. Each scenario ran three times through FastAPI `TestClient`; the table reports median and maximum end-to-end request time.

Host: Apple-silicon laptop class (8 CPU cores, 8 GB unified memory). Device and OS identifiers are intentionally omitted.

## Results

| Scenario | HTTP | Median ms | Max ms | Route/intent | Result | Model used |
|---|---:|---:|---:|---|---|---|
| Project status | 201 | 132.95 | 199.69 | `system_health` | Inspected; misclassified | No |
| Product roadmap | 201 | 387.84 | 424.49 | `product_review` | Plan waiting approval | No |
| Marketing analysis | 201 | 275.39 | 277.38 | `marketing_summary` | Capability succeeded | No |
| Sales follow-up draft | 201 | 420.60 | 421.16 | `business_review` | Plan waiting approval | No |
| Engineering review | 201 | 337.73 | 340.77 | `architecture_review` | CTO brief succeeded | No |
| QA regression checklist | 201 | 379.68 | 386.71 | `planning_request` | Plan waiting approval; no QA agent | No |
| Cross-department delegation | 201 | 299.73 | 357.80 | `marketing_summary` | Multi-capability plan waiting approval | No |
| Provider fallback request | 201 | 378.66 | 380.57 | `business_review` | Deterministic output | No |
| Deploy + Jira approval command | 201 | 131.87 | 137.73 | `system_health` | Connector inspection; misclassified | No |
| Cross-business isolation | 201 | 377.16 | 380.25 | `business_review` | Correct business; no foreign marker | No |

Median of scenario medians: approximately 338 ms. These results exceed the old `<50 ms` ambition for full conversation operations, but remain responsive for a local deterministic prototype. They say nothing about network model latency or production PostgreSQL contention.

## Quality Observations

- 10/10 requests returned valid HTTP responses.
- 0/10 invoked model reasoning.
- 2/10 were materially misclassified.
- 4/10 produced plans waiting for approval.
- Business marker isolation passed for the single controlled path.
- Compound action requests are vulnerable to keyword dominance.

## Test Suite

Command: unittest discovery with isolated SQLite and external providers disabled.

- Ran: 159
- Passed: 158
- Errors: 1
- Duration: 14.325 seconds
- Error: scheduler test patches `app.reasoning.service.generate_response`, which no longer exists.
- Additional output: SQLite resource warnings indicated unclosed connection objects after completion.

## Performance Risks from Code Inspection

- Context assembly performs several sequential database queries per message (`app/reasoning/context.py:44-122`).
- Capability execution is synchronous and in-process.
- Planning execution does not exploit declared parallel groups.
- Dashboard loads many APIs from a monolithic component, increasing request fan-out and render coupling.
- Startup performs schema creation, seeding, registration, and background-service startup.
- Process-local provider usage counters and semaphores do not coordinate multiple workers.

## Hypotheses Requiring Future Measurement

The following are not measured findings: PostgreSQL p95 under concurrent users, Ollama tokens/second, cloud-provider latency/cost, dashboard Largest Contentful Paint, scheduler CPU impact, and connector rate-limit behavior. Measure these only after canonical workflows and provider clients are stabilized.

