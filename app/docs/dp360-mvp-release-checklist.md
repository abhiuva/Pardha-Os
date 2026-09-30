# DP360 MVP Release Checklist

Owner: Codex / Founder
Scope: SPRINT-001 Pardha DP360 MVP
Release type: workable local prototype

## Release Goal

Pardha must run as a cloud-assisted, tool-driven agent OS for DP360 Commerce without requiring Ollama, a local GPU, or destructive external connector writes.

## Required Environment

```bash
PARDHA_REASONING_PROVIDER=deterministic
PARDHA_REASONING_FALLBACK=deterministic
PARDHA_OLLAMA_ENABLED=false
PARDHA_CONNECTOR_MODE=mock
```

Optional live connector credentials may be configured, but local MVP validation must pass without them.

## Backend Gate

Run from `pardha-core`:

```bash
./venv/bin/python -m unittest \
  tests.test_reasoning \
  tests.test_sprint_001_dp360_mvp \
  tests.test_mcp_runtime \
  tests.test_hubspot_connector \
  tests.test_lead_qualification \
  tests.test_demo_booking_workflow \
  tests.test_post_demo_drafts \
  tests.test_meta_ingestion \
  tests.test_meta_ad_approvals \
  tests.test_marketing_cockpit \
  tests.test_commercial_readiness \
  -v
```

Pass criteria:

- Reasoning gateway starts with deterministic provider.
- Ollama is optional and idle by default.
- DP360 command center returns populated CEO, PM, CTO, Sales, and Marketing surfaces.
- HubSpot, Meta, and Instagram connector contracts work in mock read mode.
- Lead qualification, demo booking, post-demo follow-up, and proposal draft workflows pass.
- Marketing KPI and campaign health APIs return zero-safe metrics and approval-gated recommendations.
- Commercial connector status reports real authentication state.

## Frontend Gate

Run from `pardha-core/dashboard`:

```bash
npm run build
```

Pass criteria:

- Vite production build succeeds.
- DP360 Command Center route is available at `/?page=DP360%20Command`.
- Dashboard can render the commercial command center payload without broken imports.

## Connector Contract Gate

Run from `pardha-core`:

```bash
./venv/bin/python -m unittest \
  tests.test_hubspot_connector \
  tests.test_meta_ingestion \
  tests.test_meta_ad_approvals \
  tests.test_mcp_runtime \
  -v
```

Pass criteria:

- Read-only mock-contract mode returns stable records.
- Missing live credentials produce honest unavailable or mock status.
- external writes are blocked without explicit founder approval.
- Approval decisions are audited and do not perform external writes in tests.

## Smoke Gate

Start backend:

```bash
./venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Start dashboard:

```bash
cd dashboard
npm run dev -- --host 127.0.0.1 --port 5174
```

Verify:

```text
GET http://127.0.0.1:8000/commercial/dp360-command-center
GET http://127.0.0.1:8000/commercial/connectors/status
GET http://127.0.0.1:8000/ai/providers/status
GET http://127.0.0.1:8000/marketing/kpis
GET http://127.0.0.1:8000/marketing/campaign-health
GET http://127.0.0.1:8000/sales/dashboard
```

Dashboard URL:

```text
http://127.0.0.1:5174/?page=DP360%20Command
```

Pass criteria:

- Backend returns HTTP 200 for every smoke endpoint.
- Dashboard loads the DP360 Command Center.
- No local Ollama process is required.
- No external writes occur.

## Release Blockers

- Backend test gate fails.
- Frontend build fails.
- DP360 command center has empty executive, sales, or marketing surfaces.
- Connector status returns fake connected state.
- Demo booking or post-demo proposal generation cannot complete in mock mode.
- Any test attempts destructive external writes without founder approval.

## Release Decision

Release may be marked ready only when Backend Gate, Frontend Gate, Connector Contract Gate, and Smoke Gate all pass.
