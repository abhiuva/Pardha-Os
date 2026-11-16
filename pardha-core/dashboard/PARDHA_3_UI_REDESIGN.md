# Pardha 3.0 Product Experience Redesign

## Navigation

1. Executive Dashboard
2. Ask Pardha
3. Businesses
4. Agents
5. Knowledge
6. Marketing
7. Sales
8. Product Factory
9. Operations
10. Integrations
11. Analytics
12. Founder
13. Settings

## Routing And Page Hierarchy

The dashboard uses a workflow-first page map in `src/App.jsx`. The local route is still the Vite single-page app, with `?page=` support for direct validation:

- `?page=Executive%20Dashboard`
- `?page=Ask%20Pardha`
- `?page=Businesses`
- `?page=Agents`
- `?page=Knowledge`
- `?page=Marketing`
- `?page=Sales`
- `?page=Product%20Factory`
- `?page=Operations`
- `?page=Integrations`
- `?page=Analytics`
- `?page=Founder`
- `?page=Settings`

Page responsibility:

- Executive Dashboard: daily brief, goal, business health, approvals, recommendations, quick actions, and voice.
- Ask Pardha: conversation, streaming, voice, history, current business, reasoning timeline, capability details, and suggested actions.
- Businesses: business context selection and workspace creation.
- Agents: all AI operators with status, current task, capabilities, memory, history, and performance.
- Marketing: campaigns, leads, analytics, insights, recommendations, KPIs, and voice context.
- Product Factory: PRDs, roadmap/sprint artifacts, Jira/GitHub-oriented workflow, QA, approvals, and releases.
- Integrations: health, authentication, capabilities, latency, and logs for each connector.
- Settings: administration, security, diagnostics, and migration notes.

## Migration Plan

1. Keep backend APIs unchanged.
2. Replace module-first tabs with Founder workflow navigation.
3. Move old homepage technical counters into their responsible pages.
4. Make Executive Dashboard business-facing only.
5. Make Ask Pardha the primary creation and command surface.
6. Keep business context visible before operational and administrative tools.
7. Move technical diagnostics and enterprise administration to Settings.
8. Validate each major page with screenshots before merging to `develop`.

## Founder Walkthrough

1. Start on Executive Dashboard and read the executive brief.
2. Review Today's Goal and Pending Approvals.
3. Use Quick Actions or floating voice to ask Pardha what to do next.
4. Move into Ask Pardha for conversation, reasoning timeline, suggested actions, and capability details.
5. Switch Businesses only when the operating context changes.
6. Open Agents to inspect which operator is working and what it remembers.
7. Use Marketing, Sales, and Product Factory for dedicated execution workflows.
8. Use Operations and Integrations for execution status and connector health.
9. Use Settings only for administration and system diagnostics.

## Executive Voice Runtime

Voice is global and page-aware. The active page is sent as `module_context` with every streamed conversation request.

Runtime pipeline:

1. Microphone
2. Speech-to-text
3. Conversation memory
4. Business context
5. Intent detection
6. Capability discovery
7. Reasoning gate
8. Ollama Qwen
9. Planner
10. Execution
11. Response composer
12. Streaming
13. Text-to-speech

Supported runtime states:

- wake
- listening
- transcribing
- thinking
- planning
- executing
- speaking
- completed
- error

Voice modes:

- push-to-talk
- interruptible response
- continuous conversation

Ollama model manager:

- default model: `qwen3:8b`
- on-demand model start
- manual model stop
- idle timeout unload
- runtime model switching
- health monitoring and diagnostics
- displayed diagnostics: current model, latency, tokens, context size, reasoning status, and 100-scenario validation score

Validation:

- `GET /api/conversations/voice-validation` runs 100 runtime scenarios across microphone contract, speech-to-text contract, Qwen reasoning contract, conversation, memory, business context, execution, streaming, speech, and error recovery.
- Browser microphone and speech output still require manual permission validation in Chrome or another Web Speech API browser.
