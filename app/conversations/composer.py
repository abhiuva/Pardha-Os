from __future__ import annotations

import json
import re
from typing import Any

from app.conversations.runtime_inspector import inspect_runtime, relevant_connectors
from app.conversations.schemas import ConversationResponsePayload, SuggestedAction
from app.reasoning.client import OllamaUnavailable, generate_response, ollama_status


INTERNAL_TERMS = (
    "routed",
    "capability executed",
    "capability_id",
    "execution adapter",
    "intelligence kernel",
    "registered capability",
)


def compose_executive_response(
    *,
    founder_message: str,
    intent: str,
    conversation_type: str,
    context: dict[str, Any],
    structured_payload: ConversationResponsePayload,
    source_output: Any = None,
    execution_ms: int = 0,
) -> ConversationResponsePayload:
    runtime = inspect_runtime(founder_message, context)
    reasoning = _reasoning_decision(founder_message, intent, source_output, runtime)
    response_text = _deterministic_response(
        founder_message=founder_message,
        intent=intent,
        conversation_type=conversation_type,
        context=context,
        payload=structured_payload,
        source_output=source_output,
        runtime=runtime,
    )
    if reasoning["required"] and runtime["ollama"].get("connected"):
        response_text, reasoning = _ollama_response(
            founder_message=founder_message,
            intent=intent,
            context=context,
            payload=structured_payload,
            source_output=source_output,
            runtime=runtime,
            fallback=response_text,
            reasoning=reasoning,
        )

    response_text = _polish(response_text)
    transparency = {
        "intent": intent,
        "conversation_type": conversation_type,
        "business": (context.get("business") or {}).get("business_name"),
        "business_id": context.get("business_id"),
        "capabilities_used": structured_payload.capabilities_used,
        "knowledge_used": _evidence_value(structured_payload.evidence, "knowledge"),
        "planner_used": bool((structured_payload.execution or {}).get("plan_id")),
        "reasoning": reasoning,
        "verification": structured_payload.verification,
        "duration_ms": execution_ms or (structured_payload.execution or {}).get("duration_ms", 0),
        "confidence": structured_payload.confidence,
        "evidence": structured_payload.evidence,
    }
    verification = dict(structured_payload.verification or {})
    verification.update(
        {
            "composer": "executive_response_composer",
            "founder_safe": not _contains_internal_language(response_text),
            "runtime_inspected": True,
            "reasoning_used": reasoning["used"],
        }
    )
    return structured_payload.model_copy(
        update={
            "executive_summary": response_text,
            "verification": verification,
            "transparency": transparency,
            "runtime_inspection": _compact_runtime(runtime),
            "reasoning_used": reasoning["used"],
            "reasoning_provider": reasoning["provider"],
            "response_style": "executive",
        }
    )


def _deterministic_response(
    *,
    founder_message: str,
    intent: str,
    conversation_type: str,
    context: dict[str, Any],
    payload: ConversationResponsePayload,
    source_output: Any,
    runtime: dict[str, Any],
) -> str:
    text = founder_message.lower()
    business_name = (context.get("business") or {}).get("business_name") or _business_from_message(founder_message, runtime)

    if payload.verification.get("status") == "needs_clarification":
        names = [item.get("business_name") for item in runtime.get("businesses", []) if item.get("business_name")]
        suffix = f" I can use {', '.join(names[:5])}." if names else ""
        return f"I need one decision before I act: which business should I use for this request?{suffix}"

    if intent in {"executive_help", "system_health"} or "what can you do" in text or "how do you work" in text:
        return _capability_explanation(runtime, business_name)

    if any(term in text for term in ("connected", "connect", "gmail", "outlook", "jira", "whatsapp", "calendar", "github", "ollama", "voice")):
        return _diagnostic_guidance(founder_message, runtime, payload)

    if any(term in text for term in ("why", "broken", "not working", "failed", "didn't")):
        return _diagnostic_guidance(founder_message, runtime, payload)

    if (payload.execution or {}).get("plan_id"):
        execution = payload.execution or {}
        actions = _action_sentence(payload.next_recommended_actions)
        approval = " It needs your approval before execution." if execution.get("approval_required") else " It is ready for execution."
        return (
            f"Goal Created: I created an operating plan for {business_name or 'the selected business'}. "
            f"The plan is tied to a persistent goal, includes measurable KPIs, and has an execution graph ready for review.{approval} {actions}"
        ).strip()

    if intent in {"knowledge_search", "business_context", "document_lookup", "knowledge_review"}:
        knowledge = _list_from_output(source_output)
        if knowledge:
            titles = ", ".join(_title(item) for item in knowledge[:3])
            return f"I found relevant knowledge for {business_name or 'this business'}: {titles}. The strongest next step is to use this context to update the current objective or executive brief."
        return f"I did not find matching knowledge for that request yet. Upload the relevant document or broaden the search, and I can use it in the next plan."

    output_summary = _source_summary(source_output)
    if output_summary:
        return f"Based on the current {business_name or 'business'} operating context, here is the useful signal: {output_summary}"

    if payload.confidence <= 0:
        return "I do not have a working operational path for that request yet. The next useful step is to open Capability Explorer and register or repair the missing capability."

    actions = _action_sentence(payload.next_recommended_actions)
    return f"I reviewed the current {business_name or 'business'} context and completed the requested check. {actions}".strip()


def _ollama_response(**kwargs) -> tuple[str, dict[str, Any]]:
    reasoning = dict(kwargs["reasoning"])
    prompt = {
        "founder_message": kwargs["founder_message"],
        "intent": kwargs["intent"],
        "business": (kwargs["context"].get("business") or {}).get("business_name"),
        "evidence": kwargs["payload"].evidence[:6],
        "execution": kwargs["payload"].execution,
        "verification": kwargs["payload"].verification,
        "source_output": kwargs["source_output"],
    }
    try:
        response = generate_response(
            json.dumps(prompt, default=str)[:7000],
            (
                "You are Pardha, an executive Chief of Staff. Write a concise founder-facing answer. "
                "Do not expose API names, capability IDs, adapters, or internal services unless explicitly requested. "
                "Include the assessment, evidence basis, recommendation, and next action."
            ),
        )
        reasoning.update({"used": True, "provider": "ollama", "error": None})
        return response, reasoning
    except (OllamaUnavailable, OSError, TimeoutError) as exc:
        reasoning.update({"used": False, "provider": "deterministic", "error": str(exc)})
        return kwargs["fallback"], reasoning


def _reasoning_decision(message: str, intent: str, source_output: Any, runtime: dict[str, Any]) -> dict[str, Any]:
    text = message.lower()
    complex_terms = ("strategy", "analyze", "recommend", "why", "roadmap", "plan", "growth", "retention", "risk", "review")
    required = any(term in text for term in complex_terms) or intent in {"business_review", "product_review", "architecture_review", "business_strategy"}
    return {
        "required": required,
        "used": False,
        "provider": "deterministic",
        "model": runtime.get("ollama", {}).get("current_model") or ollama_status().current_model,
        "reason": "complex_request" if required else "deterministic_platform_sufficient",
    }


def _capability_explanation(runtime: dict[str, Any], business_name: str | None) -> str:
    caps = runtime.get("capabilities", {})
    connectors = runtime.get("connectors", [])
    connected = [item for item in connectors if item.get("connected")]
    businesses = runtime.get("businesses", [])
    knowledge_count = runtime.get("knowledge", {}).get("count", 0)
    running = runtime.get("runtime", {}).get("running_executions", 0)
    return (
        f"Here is what I can do right now. I can work across {len(businesses)} businesses"
        f"{f', including {business_name}' if business_name else ''}; inspect {knowledge_count} knowledge records in the current context; "
        f"use {caps.get('total', 0)} registered operating capabilities; check {len(connectors)} integrations with {len(connected)} live-authenticated; "
        f"and monitor {running} active execution. Ask me for a brief, roadmap, connector diagnosis, knowledge search, project review, task plan, or execution status."
    )


def _diagnostic_guidance(message: str, runtime: dict[str, Any], payload: ConversationResponsePayload) -> str:
    text = message.lower()
    connectors = relevant_connectors(runtime, text)
    if "voice" in text:
        return (
            "Voice depends on browser microphone permission, SpeechRecognition support, and speech synthesis. "
            "If it listens but does not answer, check microphone permission first, then confirm the conversation stream reaches the backend."
        )
    if "ollama" in text:
        ollama = runtime.get("ollama", {})
        if ollama.get("connected"):
            return f"Ollama is available. The active model is {ollama.get('current_model')}, and reasoning is used only when the request needs it."
        return f"Ollama is not active. Root cause: {ollama.get('message') or 'local model service unavailable'}. Enable it with the configured environment and make sure the model is installed."
    if connectors:
        broken = [item for item in connectors if not item.get("connected")]
        if broken:
            item = broken[0]
            missing = item.get("missing_environment") or []
            fix = f" Set {', '.join(missing)}." if missing else " Reconnect the account and run Test Connection."
            return (
                f"{item.get('name')} is not connected. Root cause: {item.get('authentication_status')} with health `{item.get('health')}`."
                f"{fix} I will treat it as unavailable until the connector reports a real authenticated account."
            )
        names = ", ".join(item.get("name", "Connector") for item in connectors)
        return f"{names} is connected and available. I can use its status in planning and execution checks."
    if payload.verification:
        return f"I inspected the runtime path. Current verification says: {payload.verification.get('summary', 'no failure detail was reported')}."
    return "I inspected the runtime but did not find a specific failing connector or execution. Ask me about the exact service or task and I will narrow the diagnosis."


def _source_summary(source_output: Any) -> str:
    if source_output is None:
        return ""
    if hasattr(source_output, "model_dump"):
        source_output = source_output.model_dump(mode="json")
    if isinstance(source_output, list):
        return f"{len(source_output)} records are available for review." if source_output else ""
    if isinstance(source_output, dict):
        for key in ("summary", "executive_summary", "message", "status"):
            if source_output.get(key):
                return str(source_output[key])
        for key in ("recommendations", "risks", "top_priorities", "recommended_actions"):
            value = source_output.get(key)
            if isinstance(value, list) and value:
                return "; ".join(str(item) for item in value[:3])
    return str(source_output)[:260]


def _list_from_output(source_output: Any) -> list[Any]:
    if isinstance(source_output, list):
        return source_output
    if hasattr(source_output, "model_dump"):
        source_output = source_output.model_dump(mode="json")
    if isinstance(source_output, dict):
        for value in source_output.values():
            if isinstance(value, list):
                return value
    return []


def _title(item: Any) -> str:
    if hasattr(item, "model_dump"):
        item = item.model_dump(mode="json")
    if isinstance(item, dict):
        return str(item.get("title") or item.get("name") or item.get("knowledge_id") or "knowledge item")
    return str(item)[:80]


def _business_from_message(message: str, runtime: dict[str, Any]) -> str | None:
    lowered = message.lower()
    for item in runtime.get("businesses", []):
        name = item.get("business_name")
        if name and name.lower() in lowered:
            return name
    return None


def _action_sentence(actions: list[SuggestedAction]) -> str:
    if not actions:
        return "The next step is to review the evidence and decide whether to execute."
    labels = [item.label for item in actions[:2]]
    return f"Recommended next step: {labels[0]}." if len(labels) == 1 else f"Recommended next steps: {labels[0]} and {labels[1]}."


def _evidence_value(evidence: list[dict[str, Any]], evidence_type: str) -> Any:
    for item in evidence:
        if item.get("type") == evidence_type:
            return item.get("value")
    return None


def _compact_runtime(runtime: dict[str, Any]) -> dict[str, Any]:
    return {
        "database": runtime.get("database"),
        "businesses": {"count": len(runtime.get("businesses", [])), "items": runtime.get("businesses", [])[:8]},
        "knowledge": runtime.get("knowledge"),
        "capabilities": {key: value for key, value in runtime.get("capabilities", {}).items() if key != "items"},
        "connectors": runtime.get("connectors", []),
        "ollama": runtime.get("ollama"),
        "runtime": runtime.get("runtime"),
        "learning": runtime.get("learning", []),
    }


def _contains_internal_language(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in INTERNAL_TERMS)


def _polish(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    cleaned = cleaned.replace("`", "")
    return cleaned
