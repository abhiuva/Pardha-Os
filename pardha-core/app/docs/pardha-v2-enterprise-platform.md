# Pardha v2.0 Sprint 8 - Enterprise Platform

## Mission

Sprint 8 stabilizes Pardha as a commercial SaaS foundation for paying customers. It adds tenant isolation, RBAC, enterprise security primitives, audit logging, observability, billing architecture, administration, deployment profiles, AI governance, and feature flags.

No new AI agents were added. Planning, conversation, and execution engines are reused through the existing platform.

## Architecture

```text
Customer
  -> Tenant
  -> Businesses
  -> Departments
  -> Capabilities
  -> Conversation
  -> Execution
  -> Audit
  -> Analytics
```

The Enterprise Platform is implemented as an additive module:

- `app/enterprise/router.py` exposes enterprise APIs.
- `app/enterprise/service.py` owns tenant, RBAC, audit, observability, billing, integration, deployment, governance, and flag logic.
- `app/enterprise/schemas.py` defines API contracts.
- `app/db/models.py` stores enterprise persistence models.
- `dashboard/src/App.jsx` adds the Enterprise dashboard tab.

## Database Schema

Migration: `migrations/023_create_enterprise_platform.sql`

New tables:

- `tenants`
- `tenant_users`
- `auth_refresh_tokens`
- `audit_logs`
- `observability_metrics`
- `billing_subscriptions`
- `enterprise_integrations`
- `deployment_profiles`
- `ai_governance_records`
- `feature_flags`

Extended tables:

- `businesses.tenant_id`
- `auth_users.tenant_id`

## RBAC

RBAC is capability-based. Supported roles:

- Founder
- CEO
- Product Manager
- Engineering Manager
- Developer
- QA
- Marketing
- Sales
- Customer Success
- Finance
- Operations
- Viewer

The matrix is exposed by `GET /enterprise/rbac`.

## Enterprise APIs

- `POST /enterprise/tenants`
- `GET /enterprise/tenants`
- `GET /enterprise/users`
- `GET /enterprise/rbac`
- `POST /enterprise/audit`
- `GET /enterprise/audit`
- `GET /enterprise/observability`
- `GET /enterprise/billing`
- `GET /enterprise/integrations`
- `GET /enterprise/deployment/profiles`
- `GET /enterprise/governance`
- `POST /enterprise/feature-flags`
- `GET /enterprise/feature-flags`
- `GET /enterprise/security`
- `GET /enterprise/dashboard`
- `GET /enterprise/admin`
- `GET /enterprise/validation`

## Security Foundation

Implemented:

- JWT token issuance on login.
- Hashed refresh token persistence.
- Session records.
- Password policy checks.
- MFA-ready status contract.
- Secure HTTP response headers.
- Configurable rate limiting through `PARDHA_RATE_LIMIT_MAX`.
- Explicit CORS allow-list for the local dashboard.
- Environment-based secrets.

Production must set:

- `PARDHA_JWT_SECRET`
- `PARDHA_ADMIN_EMAIL`
- `PARDHA_ADMIN_PASSWORD`
- `DATABASE_URL`

## Audit Platform

Audit records track:

- Actor
- Tenant
- Business
- Capability
- Conversation
- Approval
- Execution
- Resource
- Outcome
- Rollback metadata
- IP address
- User agent

The API middleware records request-level audit events. Domain-specific actions can call `POST /enterprise/audit`.

## Observability

`GET /enterprise/observability` reports:

- System metrics
- Execution metrics
- Conversation metrics
- Planner metrics
- Capability metrics
- API metrics
- Queue metrics
- Performance metrics
- Alert list

## Billing Foundation

Billing architecture supports:

- Free Trial
- Starter
- Professional
- Enterprise

Tracked dimensions:

- Users
- Businesses
- Knowledge storage
- Executions
- AI usage
- Storage
- Integrations

No payment gateway is included in Sprint 8.

## Enterprise Integrations

OAuth-ready provider records are created for:

- Google
- Microsoft
- Atlassian
- GitHub
- Slack
- Teams

Each provider stores status, auth type, scopes, credential reference, rotation status, health, and last sync metadata. Secrets are referenced, not stored as source code.

## Deployment Profiles

Default profiles:

- Development
- Testing
- Staging
- Production

Each profile tracks Docker readiness, Kubernetes readiness, health checks, backup policy, restore policy, and configuration state.

## AI Governance

Governance records support:

- Reasoning provider
- Model version
- Prompt version
- Capability used
- Conversation ID
- Confidence
- Evidence
- Human approval

This keeps future AI provider switching auditable without changing the existing agents.

## Feature Flags

Feature flags support:

- Enable / disable
- Beta features
- Tenant-specific flags
- Rollout percentages
- Emergency disable

## Dashboard

The Enterprise dashboard tab displays:

- Tenant health
- Business isolation
- Users
- Audit activity
- Validation score
- Security readiness
- Billing usage
- Observability metrics
- RBAC roles
- Enterprise integrations
- Deployment profiles
- Feature flags
- AI governance
- Administration console

## Validation

Automated validation:

```bash
env DATABASE_URL=sqlite:////private/tmp/pardha_sprint8_full_tests.db \
  PARDHA_ADMIN_EMAIL=founder@pardha.local \
  PARDHA_ADMIN_PASSWORD=test-admin-password \
  PARDHA_OLLAMA_ENABLED=false \
  PARDHA_RATE_LIMIT_MAX=1000 \
  ./venv/bin/python -m unittest discover -s tests
```

Sprint 8 endpoint validation:

```bash
curl http://127.0.0.1:8000/enterprise/validation
```

Expected:

- `scenarios_run >= 200`
- `score >= 98`
- Multi-tenancy operational
- RBAC operational
- Audit operational
- Billing architecture operational
- Deployment profiles operational
- Enterprise security ready

## Known Limitations

- OAuth providers are configuration-ready but not completing live OAuth authorization flows yet.
- Billing has plan and usage architecture but no payment gateway.
- Encryption at rest depends on the production database and storage layer configuration.
- Existing PostgreSQL databases must apply migration `023_create_enterprise_platform.sql` before running Sprint 8 models.
- AI governance records are stored, but provider switching remains future-ready infrastructure.
