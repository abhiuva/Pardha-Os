# Pardha Developer Setup

Verified on 2026-11-16 on macOS (Apple silicon) with **Python 3.14.6** and Node 23.11.0, against
`develop` after PR #3 and PR #4 (`97890a1`). Other Python versions have **not** been verified.
Commands work in `bash` and `zsh`.

## 1. Clone

```bash
git clone https://github.com/abhiuva/Pardha-Os.git
cd Pardha-Os
git switch develop        # development baseline; feature branches start here
```

## 2. Backend install

```bash
cd pardha-core
python3 --version         # verified with 3.14.6; use that version where possible
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

`requirements.txt` is unpinned. A fresh install may resolve newer versions than the
[historical dependency-resolution snapshot](audits/sprint0/evidence/pip-freeze-py314.txt) recorded on
2026-11-16. That file is evidence of what was tested, **not a lock file**.

## 3. Safe local environment

All remaining commands run from `pardha-core/`. Define these two lists once per shell session. They
are only used to build each command's own environment: your real shell environment and credentials
are never modified or deleted.

```bash
# Background services off, mock connectors, deterministic reasoning, Jira disabled.
PARDHA_SAFE_ENV=(
  PARDHA_CONNECTOR_MODE=mock
  PARDHA_OLLAMA_ENABLED=false
  PARDHA_REASONING_PROVIDER=deterministic
  PARDHA_REASONING_FALLBACK=deterministic
  PARDHA_KNOWLEDGE_WATCHER_ENABLED=false
  PARDHA_SCHEDULER_ENABLED=false
  PARDHA_JIRA_ENABLED=false
  PARDHA_EXTERNAL_WRITES_ENABLED=false   # emergency write lockdown; enforced once PE0OM-75 is merged
)

# Live provider/connector credentials and network switches, removed per process with `env -u`.
PARDHA_UNSET_CREDENTIALS=(
  -u DATABASE_URL
  -u OPENAI_API_KEY
  -u JIRA_URL -u JIRA_EMAIL -u JIRA_API_TOKEN -u JIRA_PROJECT_KEY
  -u HUBSPOT_ACCESS_TOKEN -u HUBSPOT_PORTAL_ID
  -u META_ACCESS_TOKEN -u META_AD_ACCOUNT_ID -u META_BUSINESS_ACCOUNT_ID
  -u META_INSTAGRAM_ACCOUNT_ID -u META_PAGE_ID
  -u GITHUB_TOKEN
  -u GMAIL_CLIENT_ID -u GMAIL_CLIENT_SECRET -u GMAIL_REFRESH_TOKEN -u PARDHA_GMAIL_ACCESS_TOKEN
  -u OUTLOOK_CLIENT_ID -u OUTLOOK_CLIENT_SECRET -u OUTLOOK_REFRESH_TOKEN -u OUTLOOK_TENANT_ID
  -u PARDHA_OUTLOOK_ACCESS_TOKEN
  -u GOOGLE_CALENDAR_CLIENT_ID -u GOOGLE_CALENDAR_CLIENT_SECRET -u GOOGLE_CALENDAR_REFRESH_TOKEN
  -u PARDHA_WHATSAPP_ACCESS_TOKEN -u PARDHA_WHATSAPP_PHONE_NUMBER_ID
  -u PARDHA_COMMUNICATIONS_ENABLE_NETWORK -u PARDHA_WHATSAPP_ENABLE_NETWORK
)
```

**Never run tests or the backend without an explicit `DATABASE_URL`.** The application's default is
the local PostgreSQL database `pardha_core`, which must never be used by tests.

These settings reduce local risk only. They **do not replace** backend authentication, project
authorization or human approval (HITL) of external writes, which are being implemented under PE0OM-56.

## 4. Run the tests (new disposable database every run)

Each run creates a fresh SQLite database in a new temporary directory and deletes that directory
when the run ends, whether it passes or fails. The block's exit code is the test run's exit code.
The test database is separate from the runtime database in section 5.

```bash
(
  set -eu
  TEST_DB_DIR="$(mktemp -d)"
  trap '[ -n "$TEST_DB_DIR" ] && rm -rf -- "$TEST_DB_DIR"' EXIT
  TEST_DATABASE_URL="sqlite:///$TEST_DB_DIR/pardha_test.db"
  # Pre-flight: refuse anything that is not a fresh file in the new temporary directory.
  [ ! -e "$TEST_DB_DIR/pardha_test.db" ] || { echo "Refusing: test database already exists" >&2; exit 1; }
  env "${PARDHA_UNSET_CREDENTIALS[@]}" "${PARDHA_SAFE_ENV[@]}" \
    DATABASE_URL="$TEST_DATABASE_URL" \
    PARDHA_JWT_SECRET="$(openssl rand -hex 32)" \
    ./venv/bin/python -m unittest discover -s tests
)
```

Expected on `develop` (`97890a1`): `Ran 155 tests` and `OK`. SQLite `ResourceWarning` messages about
unclosed connections are a known, pre-existing issue.

Code-level enforcement (tests refuse to start on an unset, developer or non-disposable database) is
being added under PE0OM-75 and isn't on `develop` yet. Until it is, these commands are the safeguard.

## 5. Run the backend (separate runtime database)

The runtime database is a persistent local SQLite file outside the repository, separate from the
test database. Bind to localhost only: the API is not yet authenticated and must not be exposed.

```bash
PARDHA_DEV_DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/pardha-dev"
mkdir -p "$PARDHA_DEV_DATA_DIR"
env "${PARDHA_UNSET_CREDENTIALS[@]}" "${PARDHA_SAFE_ENV[@]}" \
  DATABASE_URL="sqlite:///$PARDHA_DEV_DATA_DIR/pardha_dev.db" \
  PARDHA_JWT_SECRET="$(openssl rand -hex 32)" \
  ./venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In a second terminal: `curl http://127.0.0.1:8000/` returns `{"name":"Pardha","status":"alive"}`.
A new random `PARDHA_JWT_SECRET` per start invalidates earlier local sessions, which is intended.

## 6. Dashboard

```bash
cd dashboard              # from pardha-core/
npm ci
npm run build                                   # production build
npm run dev -- --host 127.0.0.1 --port 5174     # dev server; backend CORS allows 5174 only
```

The Vite dev server proxies `/api` calls to `http://127.0.0.1:8000`. Only `npm run build` was
verified on 2026-11-16; the dev server wasn't exercised.
