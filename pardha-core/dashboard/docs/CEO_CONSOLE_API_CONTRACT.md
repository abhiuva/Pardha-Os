# CEO Console API Contract

## Scope

Wave 1 reuses the committed Pardha APIs. It does not depend on the uncommitted
`/ceo-agent/*` prototype and does not introduce backend routes.

| Experience | API |
|---|---|
| Business list | `GET /businesses` |
| Executive command | `POST /conversations/stream` |
| Goals | `GET /planning/goals?business_id=...` |
| Tasks | `GET /tasks?business_id=...` |
| Executions | `GET /runtime/executions?business_id=...` |
| Approvals | `GET /planning/approvals?business_id=...` |
| Internal delegation | `POST /objectives` |
| Approval decision | `POST /planning/plans/{plan_id}/{approve|reject}` |

All CEO Console requests send the current session bearer token. Every returned
business-owned record must match the selected `business_id`; a mixed response fails
closed and clears the workspace. Switching businesses is local to the request and
does not call the process-global `/context/switch` endpoint.

## Approval Gate

The approval drawer is visible, but decisions remain disabled unless
`GET /auth/security` explicitly reports both:

- `authorization_enforced: true`
- `authenticated_approval_identity: true`

The current `develop` response does not provide those guarantees. The UI therefore
does not submit a client-asserted founder identity. Approval enablement depends on a
future authenticated backend contract and must not be inferred from a successful
login alone.

## Response Transparency

The console renders the conversation response's provider, model, fallback state,
evidence, capabilities, recommended actions, timeline, and errors. Missing metadata
is shown as missing or not reported; it is never replaced with a success value.

Browser speech recognition is opt-in. Captured text remains editable and is not sent
until the founder chooses **Run command**. Text input remains the fallback.
