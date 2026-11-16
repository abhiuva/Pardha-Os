# Pardha Developer Setup

Verified on 2026-11-16 from a fresh clone (PR #1 head `13c2195`, re-verified on the merged
`main` `a924fcc` and `develop` `08e4bf5`), macOS (Apple Silicon), Python 3.14.6, Node 23.11.0.
Commands run from the repository root unless stated.

## 1. Clone

```bash
git clone https://github.com/abhiuva/Pardha-Os.git
cd Pardha-Os
git switch develop        # development baseline; feature branches start here
```

## 2. Backend

```bash
cd pardha-core
python3.14 -m venv venv
./venv/bin/pip install -r requirements.txt
```

`requirements.txt` is unpinned. The set that was verified is in
`docs/audits/sprint0/evidence/pip-freeze-py314.txt`.

### Safe local environment

**Always set `DATABASE_URL` explicitly.** The default is local PostgreSQL
`pardha_core`, and many tests don't override it.

```bash
export DATABASE_URL="sqlite:///$PWD/pardha_local.db"   # *.db is git-ignored
export PARDHA_CONNECTOR_MODE=mock
export PARDHA_OLLAMA_ENABLED=false
export PARDHA_REASONING_PROVIDER=deterministic
export PARDHA_REASONING_FALLBACK=deterministic
export PARDHA_JWT_SECRET="$(openssl rand -hex 32)"     # always set a strong random value
```

Leave `OPENAI_API_KEY`, `JIRA_*`, `HUBSPOT_*`, `META_*` and `PARDHA_WHATSAPP_*` unset unless
a story explicitly approves live access.

### Run

```bash
./venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
curl http://127.0.0.1:8000/          # {"name":"Pardha","status":"alive"}
```

### Tests

```bash
./venv/bin/python -m unittest discover -s tests
```

Expected on the `develop` baseline `08e4bf5`: 155 tests, 1 known error
(`test_agent_scheduler.test_normal_cycle_never_invokes_ollama`, a stale mock target),
fixed by PE0OM-72 (PR #3). After that merges: 155 tests, OK.

## 3. Dashboard

```bash
cd pardha-core/dashboard
npm ci
npm run build                                   # production build
npm run dev -- --host 127.0.0.1 --port 5174     # dev server; backend CORS allows 5174 only
```

The Vite dev server proxies API calls to `http://127.0.0.1:8000`.
Only `npm run build` was verified on 2026-11-16. The dev server wasn't exercised.
