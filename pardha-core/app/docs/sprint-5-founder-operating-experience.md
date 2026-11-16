# Sprint 5 Founder Operating Experience

## Scope

Sprint 5 adds the Founder Experience, voice interface, and Mission Control layer on top of existing Pardha services. It does not add new AI agents and does not change the Agent Registry, Event Bus, Memory Engine, or existing agent APIs.

## Backend Modules

- `app/chief_of_staff/router.py`
- `app/chief_of_staff/service.py`
- `app/chief_of_staff/schemas.py`

## Database

Migration:

- `migrations/017_create_chief_of_staff.sql`

Tables:

- `chief_conversations`
- `chief_messages`
- `founder_goals`

These tables persist founder conversations, routed assistant responses, and founder goals that are converted into existing objectives, plans, tasks, timelines, and daily follow-ups.

## APIs

- `POST /chief/chat`
- `GET /chief/conversations`
- `GET /chief/conversations/{conversation_id}`
- `POST /chief/goals`
- `GET /chief/goals`
- `GET /chief/executive-command`
- `GET /chief/help`

## UI

Dashboard experience:

- Enterprise mission landing surface: `PARDHA / Chief of Staff / Ready`
- Founder workspace as the home screen
- `Ask Pardha`
- `Goals`
- `Planning`
- `Runtime`
- `Executive Command`
- `Help`
- `Knowledge`
- `Connector Status`

Founder workspace additions:

- Business status and executive greeting
- Today's priorities, health, approvals, notifications and department status
- Chief of Staff quick actions
- Recent conversations
- Persistent conversation history with streaming execution phases
- Founder goal creation
- Approval review with approve/reject actions
- Department command center
- Live self-inspection help commands
- Mission Control runtime dashboard

## Intent Routing

Ask Pardha routes natural language requests to existing Pardha services:

- Sales prospect requests use Sales Executive prospect research.
- Marketing strategy requests use Marketing Executive campaign builder.
- Executive summary requests use the existing executive brief generator.
- Jira sprint requests use Jira connector issue status.
- Roadmap and objective requests use the Founder Copilot workflow.
- Engineering progress requests use CTO brief and execution history.
- Business review requests use Business Intelligence.
- Help requests use deterministic help responses.

## Voice

Voice input uses browser Web Speech APIs when available. Text-to-speech uses browser `speechSynthesis`. There is no fake microphone and no wake phrase listener in this sprint. The UI supports push-to-talk, interrupt, listening, thinking, planning, executing, speaking and completed states.

## Intelligence Orb

The dashboard now exposes a dynamic Intelligence Orb used on the mission landing and conversation page. States:

- `idle`
- `listening`
- `thinking`
- `planning`
- `executing`
- `speaking`
- `completed`

## Knowledge Center

The Knowledge Center supports drag-and-drop multi-upload through the UI and backend extraction for:

- PDF
- DOCX
- PPTX
- TXT
- Markdown
- CSV
- JSON

DOCX and PPTX extraction is implemented without new external services by reading OpenXML document content. PDF extraction uses `pypdf` when available and fails honestly when the PDF cannot provide text.

## Integrations Center

Connector status now includes:

- Gmail
- Outlook
- WhatsApp
- Jira
- Google Calendar
- GitHub
- VS Code
- Ollama

Every connector reports connected state, authentication status, health, required configuration, missing configuration, last sync and test status. Missing credentials are reported as missing; there are no fake success messages.

## Ollama

Sprint 5 does not introduce automatic Ollama execution. The conversational layer is deterministic and routes to existing services. Manual reasoning endpoints remain separate.

## Validation

Focused regression:

```bash
rm -f /private/tmp/pardha_sprint5_full_tests.db
env DATABASE_URL=sqlite:////private/tmp/pardha_sprint5_full_tests.db \
  PARDHA_ADMIN_EMAIL=founder@pardha.local \
  PARDHA_ADMIN_PASSWORD=test-admin-password \
  PARDHA_OLLAMA_ENABLED=false \
  ./venv/bin/python -m unittest discover -s tests
```

Dashboard build:

```bash
cd dashboard
npm run build
```

## Known Boundaries

- Connector setup, reconnect, and disconnect actions remain limited by the existing connector backends.
- Voice support depends on browser Web Speech API capability.
- The Chief of Staff layer does not perform autonomous background reasoning.
- Local PostgreSQL databases must be migrated before running the full suite against Postgres. SQLite validation creates the current schema from SQLAlchemy models.
