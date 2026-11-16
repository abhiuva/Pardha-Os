# Pardha 3.0 Product Hardening Item 1

## Executive Response Composer

The conversation runtime now separates internal execution from founder-facing communication.

Runtime flow:

```text
Founder message
-> Conversation session
-> Business context
-> Intent detection
-> Capability discovery / planning / execution
-> Structured payload
-> Runtime Inspector
-> Executive Response Composer
-> Founder-facing answer
-> Hidden transparency package
-> Operational learning
```

Only `app.conversations.composer.compose_executive_response` creates final assistant text. Capability and planner outputs remain structured JSON and are stored in `response_payload`.

## Runtime Inspector

`app/conversations/runtime_inspector.py` inspects live platform state:

- database and scheduler
- businesses
- business-scoped knowledge count
- conversation message count
- capability registry health
- connector status
- Ollama status
- runtime executions and queue
- founder operational learning signals

This powers prompts such as:

- `What can you do?`
- `What's connected?`
- `Which model is active?`
- `How much knowledge do you have?`
- `Why did Jira fail?`
- `How do I connect Gmail?`

## Operational Learning

Founder usage signals are stored in `founder_operational_learning`, separate from customer/business knowledge.

Captured signals:

- frequent intent
- frequent capability
- preferred business
- daily workflow
- approval pattern

## Capability Registry

Registered capabilities:

- `conversation.response_composer`
- `conversation.runtime_inspector`
- `conversation.operational_learning`

These are planner-visible and discoverable through the registry.

## Validation

Endpoints:

- `GET /conversations/validation`
- `GET /conversations/hardening-validation`

The hardening validation endpoint evaluates 200 scenario checks across:

- natural communication
- reasoning readiness
- runtime inspection
- knowledge retrieval
- conversation memory
- diagnostics
- capability explanation
- business context
- follow-up conversations
- production policy

## Founder Test Report

Validated live prompts:

- `What can you do?`
- `How do I connect Gmail?`

Expected behavior:

- no internal API names in the visible answer
- no `I routed...`
- no `Capability executed...`
- root cause and fix for connector diagnostics
- transparency available in response payload and UI panel
- operational learning signals persisted

## Known Limitations

- Ollama reasoning is used only when enabled and available; otherwise composer falls back to deterministic executive communication.
- Browser voice quality still depends on browser support for `SpeechRecognition`, microphone permission, and `speechSynthesis`.
- The 200-scenario hardening validation is a deterministic policy/runtime validation matrix, not a load test.
