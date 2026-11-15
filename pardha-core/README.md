# Pardha Core

## SPRINT-001 DP360 MVP Runtime

Pardha runs as a cloud-assisted, tool-driven agent OS. Local Ollama is optional
and disabled by default so the app can boot on laptops without GPU support.

### Reasoning Provider Configuration

```bash
PARDHA_REASONING_PROVIDER=deterministic
PARDHA_REASONING_FALLBACK=deterministic
PARDHA_OLLAMA_ENABLED=false
PARDHA_DEFAULT_REASONING_MODEL=llama3.2:3b
PARDHA_ADVANCED_REASONING_MODEL=qwen3:8b
```

Optional cloud/local providers:

```bash
OPENAI_API_KEY=
PARDHA_OPENAI_MODEL=gpt-4.1-mini
OLLAMA_URL=http://127.0.0.1:11434
```

Connector foundations use honest status reporting. Local demos may use explicit
mock-contract mode for read paths:

```bash
PARDHA_CONNECTOR_MODE=mock
HUBSPOT_ACCESS_TOKEN=
META_ACCESS_TOKEN=
META_AD_ACCOUNT_ID=
META_INSTAGRAM_ACCOUNT_ID=
```

External connector writes are not performed by the MVP connector foundations
without explicit founder approval.

### Local Development

Backend:

```bash
./venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Dashboard:

```bash
cd dashboard
npm run dev -- --host 127.0.0.1 --port 5174
```

DP360 Command Center:

```text
http://127.0.0.1:5174/?page=DP360%20Command
```

### Validation

```bash
./venv/bin/python -m unittest tests.test_reasoning tests.test_sprint_001_dp360_mvp tests.test_mcp_runtime tests.test_commercial_readiness -v
cd dashboard && npm run build
```

### DP360 MVP Release Checklist

The repeatable Codex/CI release gate is documented in
`app/docs/dp360-mvp-release-checklist.md`.

Run the focused MVP gate before demos:

```bash
./venv/bin/python -m unittest tests.test_dp360_mvp_release_checklist tests.test_reasoning tests.test_sprint_001_dp360_mvp tests.test_mcp_runtime tests.test_hubspot_connector tests.test_lead_qualification tests.test_demo_booking_workflow tests.test_post_demo_drafts tests.test_meta_ingestion tests.test_meta_ad_approvals tests.test_marketing_cockpit tests.test_commercial_readiness -v
cd dashboard && npm run build
```
