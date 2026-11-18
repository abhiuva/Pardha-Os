"""PE0OM-82 coordinator policy: the fixed rules the coordinator enforces.

Changing anything here changes what the coordinator may claim, so it goes through PR review.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

# Statuses reported for each candidate and for the run.
READY = "READY"
BLOCKED = "BLOCKED"
NOT_CONFIGURED = "NOT CONFIGURED"
NO_RUN = "NO-RUN"
CLAIMED = "CLAIMED"
ACTUALLY_STARTED = "ACTUALLY STARTED"

# Jira selection rules (PE0OM-82 acceptance criteria + PO comment of 17 Nov 2026).
SCOPE_LABELS = frozenset({"pardha-v1-dec7", "pardha-mvp"})
READY_LABEL = "ai-ready"
EXCLUDED_LABELS = frozenset({"ai-blocked", "ai-pr-review", "v1-deferred"})
ELIGIBLE_STATUSES = frozenset({"To Do"})
DONE_STATUSES = frozenset({"Done"})
ACCEPTANCE_MARKERS = ("acceptance criteria", "## done", "**done", "done:")

# Issues whose state is reported at every startup (readiness gate). A snapshot missing any of
# them is treated as incomplete/stale Jira, which is a no-run.
READINESS_GATE_KEYS = ("PE0OM-93", "PE0OM-75", "PE0OM-76", "PE0OM-77", "PE0OM-78", "PE0OM-79", "PE0OM-33")

SNAPSHOT_MAX_AGE = timedelta(minutes=30)

# Weekday kickoff window, Asia/Kolkata. Informational: nothing is scheduled automatically.
KICKOFF_TIMEZONE = "Asia/Kolkata"
KICKOFF_HOUR, KICKOFF_MINUTE = 8, 30

PROTECTED_BRANCHES = frozenset({"main", "develop", "release", "chore/publish-pardha-monorepo", "feature/PE0OM-19-reasoning-gateway"})


@dataclass(frozen=True)
class AgentPolicy:
    name: str
    owner_label: str
    budget_minutes: int
    branch_prefixes: tuple[str, ...]
    # Repository path prefixes this agent owns. Ownership of a path is decided by the LONGEST
    # matching prefix across all agents, so a narrower prefix carves territory out of a broader one.
    owned_prefixes: tuple[str, ...]


AGENTS: dict[str, AgentPolicy] = {
    "claude": AgentPolicy(
        name="claude",
        owner_label="ai-owner-claude",
        budget_minutes=180,
        branch_prefixes=("feature/", "fix/", "docs/"),
        owned_prefixes=("pardha-core/", "automation/", "docs/architecture/"),
    ),
    "codex": AgentPolicy(
        name="codex",
        owner_label="ai-owner-codex",
        budget_minutes=120,
        branch_prefixes=("codex/", "test/", "feature/"),
        owned_prefixes=("pardha-core/dashboard/", "pardha-core/tests/test_adversarial_", "pardha-core/tests/e2e/", "docs/qa/"),
    ),
}

OWNER_LABELS = {policy.owner_label: name for name, policy in AGENTS.items()}
