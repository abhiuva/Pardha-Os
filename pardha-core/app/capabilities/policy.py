"""Capability execution policy (PE0OM-75, PE0OM-56 slice 1/5).

Every capability run goes through ``execute_capability``. This policy is checked there,
before the adapter is invoked, so it applies whichever endpoint or queue the request
came from (kernel API, planning nodes, runtime nodes, direct runtime queue items,
conversations).

Classification is keyed on the *server-side adapter code*, never on the metadata a
client supplied when registering a capability (for example ``permissions``), because
registration is not yet authenticated.

The adapters below were verified read-only by source inspection on 2026-11-16: each
calls only list/get/search/status/brief functions with no database writes and no
outbound business-system calls. Any adapter not on this list, including any added in
future, is denied (fail closed) until centralized per-action HITL (PE0OM-78) can
authorize it.

Not yet enforced (later slices): authenticated caller identity (PE0OM-76) and
restriction of reads to the caller's authorized business/project (PE0OM-77). Some
read-only adapters currently return data that isn't business-scoped.
"""
from __future__ import annotations

VERIFIED_READ_ONLY_ADAPTERS = frozenset(
    {
        "business.context",
        "ceo.daily_brief",
        "pm.daily_brief",
        "cto.technical_brief",
        "knowledge.search",
        "sales.summary",
        "marketing.summary",
        "projects.catalog",
        "tasks.catalog",
        "objectives.catalog",
        "executions.catalog",
        "founder_goals.catalog",
        "jira.status",
        "diagnostics.system_health",
        "connectors.status",
        "conversation.runtime_inspector",
        "conversation.response_composer",
        "conversation.operational_learning",
    }
)

DENIED = "denied"


def capability_execution_decision(execution_adapter: str | None) -> tuple[bool, str]:
    """Return (allowed, reason) for running a capability with this adapter."""
    if not execution_adapter:
        return True, "Discovery-only capability: no adapter, no side effects."
    if execution_adapter in VERIFIED_READ_ONLY_ADAPTERS:
        return True, "Verified read-only adapter."
    return False, (
        f"Capability adapter '{execution_adapter}' is not verified read-only. Write-capable or unclassified "
        "capabilities are denied until centralized per-action founder approval (PE0OM-78) exists."
    )
