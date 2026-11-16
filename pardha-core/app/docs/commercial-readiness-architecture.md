# Pardha Commercial MVP Architecture

```mermaid
flowchart LR
    Customer[Founder / Customer] --> Dashboard[Dashboard v1.0]
    Dashboard --> BusinessAPI[Business Context API]
    Dashboard --> DemoAPI[Commercial Demo API]
    Dashboard --> KnowledgeAPI[Knowledge API]
    Dashboard --> ObjectiveAPI[Objectives API]
    Dashboard --> ExecAPI[Agent Executions API]
    Dashboard --> ConnectorAPI[Connector Status API]
    Dashboard --> HealthAPI[System Health API]
    Dashboard --> SalesAPI[Sales Executive API]
    Dashboard --> MarketingAPI[Marketing Executive API]
    Dashboard --> CopilotAPI[Founder Copilot / Customer Success API]

    DemoAPI --> BusinessDB[(PostgreSQL / Demo SQLite)]
    BusinessAPI --> BusinessDB
    KnowledgeAPI --> BusinessDB
    ObjectiveAPI --> BusinessDB
    ExecAPI --> BusinessDB
    ConnectorAPI --> BusinessDB
    HealthAPI --> BusinessDB
    SalesAPI --> BusinessDB
    MarketingAPI --> BusinessDB
    CopilotAPI --> BusinessDB

    KnowledgeAPI --> KnowledgeEngine[Knowledge Import Engine]
    ObjectiveAPI --> Collaboration[CEO -> PM -> CTO Collaboration Engine]
    Collaboration --> Tasks[Task Generation]
    Tasks --> BusinessDB

    HealthAPI --> Scheduler[Scheduler]
    HealthAPI --> Ollama[Ollama Status: On Demand Only]
    ConnectorAPI --> Gmail[Gmail Env/Auth Check]
    ConnectorAPI --> Outlook[Outlook Env/Auth Check]
    ConnectorAPI --> WhatsApp[WhatsApp Env/Auth Check]
    ConnectorAPI --> Jira[Jira Env/Auth Check]
    ConnectorAPI --> Calendar[Google Calendar Env/Auth Check]
    SalesAPI --> ICP[ICP Builder]
    SalesAPI --> Research[Prospect Research]
    SalesAPI --> CRM[CRM: Companies / Contacts / Leads / Deals / Activities]
    SalesAPI --> Outreach[Outreach Drafts]
    SalesAPI --> Demos[Demo Pipeline]
    MarketingAPI --> Campaigns[Campaign Workspace]
    MarketingAPI --> Content[Content Pipeline]
    MarketingAPI --> MarketingAnalytics[Marketing Analytics]
    CopilotAPI --> BI[Business Intelligence]
    CopilotAPI --> Success[Customer Success Workspace]
    CopilotAPI --> Presentation[Executive Presentation Mode]
```

## Runtime Profiles

- Development/demo can override `DATABASE_URL`, for example `sqlite:////private/tmp/pardha_commercial_demo.db`.
- Default production database remains `postgresql+psycopg2:///pardha_core`.
- `PARDHA_MODE` defaults to `DEVELOPMENT`; production should set `PARDHA_MODE=PRODUCTION`.
- Ollama remains disabled or idle unless explicit manual reasoning endpoints are invoked.

## Commercial Readiness Surfaces

- `GET /commercial/founder-dashboard`
- `GET /commercial/connectors/status`
- `POST /commercial/connectors/{provider}/test`
- `GET /commercial/system/health`
- `GET /commercial/demo/journey`
- `POST /commercial/demo/dp360`
- `POST /sales/prospect`
- `GET /sales/leads`
- `GET /sales/pipeline`
- `GET /sales/demos`
- `GET /sales/summary`
- `GET /sales/dashboard`
- `GET /sales/leads/{lead_id}/outreach`
- `POST /sales/leads/{lead_id}/schedule-demo`
- `POST /sales/leads/{lead_id}/stage`
- `POST /marketing/campaign`
- `GET /marketing/campaigns`
- `GET /marketing/analytics`
- `GET /marketing/content`
- `GET /marketing/summary`
- `GET /marketing/dashboard`
- `POST /copilot/founder`
- `GET /copilot/business-intelligence`
- `GET /copilot/customer-workspace`
- `GET /copilot/executive-briefs`
- `GET /copilot/health-dashboard`
- `POST /copilot/consultant`
- `POST /copilot/onboarding`
- `GET /copilot/demo-library`
- `POST /copilot/demo-library/load`
- `GET /copilot/presentation`
- `GET /copilot/commercial-readiness`
