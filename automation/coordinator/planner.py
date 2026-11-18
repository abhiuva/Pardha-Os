"""Read-only readiness evaluation: which approved tasks may be claimed, and why others may not.

The planner never writes anything. It returns a report; the CLI decides whether to act on it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from automation.coordinator import policy
from automation.coordinator.gitstate import GitState
from automation.coordinator.leases import Lease
from automation.coordinator.ownership import normalize, overlaps, reservation_problems
from automation.coordinator.sources import ApprovedQueue, Issue, QueueItem, Snapshot

try:
    from zoneinfo import ZoneInfo

    KOLKATA = ZoneInfo(policy.KICKOFF_TIMEZONE)
except Exception:  # pragma: no cover - zoneinfo data missing on the host
    KOLKATA = timezone(timedelta(hours=5, minutes=30), "IST")

FUTURE_SKEW = timedelta(minutes=5)


@dataclass
class Candidate:
    key: str
    summary: str
    agent: str | None
    parent: str | None
    approved: bool
    status: str = policy.BLOCKED
    reasons: list[str] = field(default_factory=list)
    open_prs: list[int] = field(default_factory=list)
    branch: str | None = None
    worktree: str | None = None
    paths: list[str] = field(default_factory=list)
    selected: bool = False


@dataclass
class RunReport:
    generated_at: str
    kickoff_window_open: bool
    snapshot_fetched_at: str | None
    snapshot_source: str | None
    run_status: str
    no_run_reasons: list[str]
    gate: dict[str, str]
    candidates: list[Candidate]

    @property
    def selected(self) -> list[Candidate]:
        return [c for c in self.candidates if c.selected]


def kickoff_window_open(now: datetime) -> bool:
    local = now.astimezone(KOLKATA)
    return local.weekday() < 5 and (local.hour, local.minute) >= (policy.KICKOFF_HOUR, policy.KICKOFF_MINUTE)


def has_acceptance_criteria(issue: Issue) -> bool:
    text = issue.description.lower()
    return any(marker in text for marker in policy.ACCEPTANCE_MARKERS)


def owner_agents(issue: Issue) -> list[str]:
    return sorted(policy.OWNER_LABELS[label] for label in issue.labels if label in policy.OWNER_LABELS)


def worktree_path_for(root: Path, agent: str, key: str) -> str:
    return str(Path(root) / f"{agent}-{key}")


def _issue_reasons(issue: Issue, snapshot: Snapshot, allowlisted: bool = False) -> tuple[list[str], list[str]]:
    """Returns (blocking reasons, inconsistency reasons). Inconsistencies cause a no-run when the
    issue is in the approved queue. An explicitly approved key (allowlist) does not need a scope
    label; every other rule still applies."""
    reasons: list[str] = []
    inconsistent: list[str] = []
    if not allowlisted and not (issue.labels & policy.SCOPE_LABELS):
        reasons.append(f"missing scope label ({' or '.join(sorted(policy.SCOPE_LABELS))})")
    if policy.READY_LABEL not in issue.labels:
        reasons.append(f"missing {policy.READY_LABEL} label")
    owners = owner_agents(issue)
    if len(owners) != 1:
        reasons.append(f"needs exactly one owner label, found {owners or 'none'}")
    for label in sorted(issue.labels & policy.EXCLUDED_LABELS):
        reasons.append(f"labelled {label}")
    if issue.status not in policy.ELIGIBLE_STATUSES:
        reasons.append(f"status is {issue.status!r}, expected one of {sorted(policy.ELIGIBLE_STATUSES)}")
    if not has_acceptance_criteria(issue):
        reasons.append("no acceptance criteria in the Jira description")
    for blocker in issue.blocked_by:
        blocking_issue = snapshot.issues.get(blocker)
        if blocking_issue is None:
            message = f"ambiguous dependency: blocker {blocker} is not in the Jira snapshot"
            reasons.append(message)
            inconsistent.append(f"{issue.key}: {message}")
        elif blocking_issue.status not in policy.DONE_STATUSES:
            reasons.append(f"blocked by {blocker} ({blocking_issue.status})")
    return reasons, inconsistent


def mentions(text: str, key: str) -> bool:
    """Exact Jira-key match: PE0OM-8 does not match PE0OM-82."""
    return re.search(rf"(?<![A-Za-z0-9]){re.escape(key)}(?![0-9])", text) is not None


def _open_prs(snapshot: Snapshot, key: str) -> list[int]:
    return [pr.number for pr in snapshot.open_prs if mentions(pr.head, key) or mentions(pr.title, key)]


def _item_reasons(item: QueueItem, issue: Issue, git: GitState, worktree: str, known_worktrees: set[str], branches: list[str]) -> tuple[list[str], list[str]]:
    reasons: list[str] = []
    inconsistent: list[str] = []
    agent_policy = policy.AGENTS.get(item.agent)
    if agent_policy is None:
        reasons.append(f"unknown agent {item.agent!r}")
        return reasons, inconsistent
    if owner_agents(issue) != [item.agent]:
        reasons.append(f"approved for {item.agent} but Jira owner label says {owner_agents(issue) or 'none'}")
    if item.acceptance_digest != issue.acceptance_digest:
        message = "acceptance criteria changed since the queue was approved"
        reasons.append(message)
        inconsistent.append(f"{issue.key}: {message}")
    branch = item.branch
    if not branch:
        reasons.append("no branch approved")
    else:
        if branch in policy.PROTECTED_BRANCHES:
            reasons.append(f"branch {branch} is protected")
        if not branch.startswith(agent_policy.branch_prefixes):
            reasons.append(f"branch {branch} does not use an allowed prefix {agent_policy.branch_prefixes}")
        if not mentions(branch, issue.key):
            reasons.append(f"branch {branch} does not name {issue.key}")
        if git.branch_exists(branch):
            reasons.append(f"branch {branch} already exists (never overwritten)")
    existing = sorted(name for name in branches if mentions(name, issue.key) and name != branch)
    if existing:
        reasons.append(f"existing branch(es) for {issue.key} indicate work in progress: {existing}")
    if Path(worktree).exists() or worktree in known_worktrees:
        reasons.append(f"worktree path {worktree} already exists")
    reasons.extend(reservation_problems(item.agent, list(item.paths)))
    return reasons, inconsistent


def evaluate(
    snapshot: Snapshot,
    queue: ApprovedQueue | None,
    git: GitState,
    active_leases: list[Lease],
    worktree_root: Path,
    now: datetime | None = None,
) -> RunReport:
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    no_run: list[str] = []

    age = now - snapshot.fetched_at
    if age > policy.SNAPSHOT_MAX_AGE:
        no_run.append(f"stale Jira snapshot: fetched {snapshot.fetched_at.isoformat()} ({int(age.total_seconds() // 60)} min old, max {int(policy.SNAPSHOT_MAX_AGE.total_seconds() // 60)})")
    elif age < -FUTURE_SKEW:
        no_run.append(f"Jira snapshot timestamp {snapshot.fetched_at.isoformat()} is in the future")

    gate: dict[str, str] = {}
    for key in policy.READINESS_GATE_KEYS:
        issue = snapshot.issues.get(key)
        if issue is None:
            no_run.append(f"readiness gate issue {key} missing from the Jira snapshot")
        else:
            gate[key] = issue.status
    if queue is None:
        no_run.append("no human-approved task queue supplied (preview only)")

    worktree_list = git.worktrees()
    known_worktrees = {wt.path for wt in worktree_list}
    branches = sorted(set(git.branches()) | {wt.branch for wt in worktree_list if wt.branch})
    leased_by_key = {lease.issue_key: lease for lease in active_leases}
    leased_agents = {lease.agent: lease for lease in active_leases}
    approved_keys = {item.key for item in queue.items} if queue else set()

    candidates: list[Candidate] = []
    for item in queue.items if queue else ():
        issue = snapshot.issues.get(item.key)
        candidate = Candidate(key=item.key, summary=issue.summary if issue else "", agent=item.agent or None, parent=issue.parent_key if issue else None, approved=True, branch=item.branch or None, paths=list(item.paths))
        if issue is None:
            candidate.reasons.append("approved issue is not in the Jira snapshot")
            no_run.append(f"{item.key}: approved issue missing from the Jira snapshot")
            candidates.append(candidate)
            continue
        candidate.worktree = worktree_path_for(worktree_root, item.agent, item.key)
        issue_reasons, issue_inconsistent = _issue_reasons(issue, snapshot, allowlisted=True)
        item_reasons, item_inconsistent = _item_reasons(item, issue, git, candidate.worktree, known_worktrees, branches)
        candidate.reasons.extend(issue_reasons + item_reasons)
        no_run.extend(issue_inconsistent + item_inconsistent)
        candidate.open_prs = _open_prs(snapshot, item.key)
        if candidate.open_prs:
            candidate.reasons.append(f"open PR(s) for this issue: {candidate.open_prs}")
        if item.key in leased_by_key:
            lease = leased_by_key[item.key]
            candidate.reasons.append(f"already leased to {lease.agent} until {lease.expires_at}")
        elif item.agent in leased_agents:
            candidate.reasons.append(f"{item.agent} already has an active story ({leased_agents[item.agent].issue_key})")
        for lease in active_leases:
            for mine in item.paths:
                for theirs in lease.paths:
                    try:
                        clash = overlaps(normalize(mine), theirs)
                    except ValueError:
                        clash = False
                    if clash and lease.issue_key != item.key:
                        candidate.reasons.append(f"path {mine!r} overlaps active reservation {theirs!r} ({lease.issue_key})")
        candidate.status = policy.BLOCKED if candidate.reasons else policy.READY
        candidates.append(candidate)

    # Informational: other ready-labelled in-scope issues that nobody has approved yet.
    for issue in sorted(snapshot.issues.values(), key=lambda i: i.key):
        if issue.key in approved_keys or policy.READY_LABEL not in issue.labels or not (issue.labels & policy.SCOPE_LABELS):
            continue
        owners = owner_agents(issue)
        candidate = Candidate(key=issue.key, summary=issue.summary, agent=owners[0] if len(owners) == 1 else None, parent=issue.parent_key, approved=False)
        candidate.reasons.extend(_issue_reasons(issue, snapshot)[0])
        candidate.open_prs = _open_prs(snapshot, issue.key)
        if candidate.open_prs:
            candidate.reasons.append(f"open PR(s) for this issue: {candidate.open_prs}")
        candidate.reasons.append("not in the human-approved queue")
        candidates.append(candidate)

    # Selection: at most one approved READY task per agent, first in queue order, with no path
    # overlap between the agents' selections.
    if not no_run:
        chosen: dict[str, Candidate] = {}
        for candidate in candidates:
            if not candidate.approved or candidate.status != policy.READY:
                continue
            if candidate.agent in chosen:
                candidate.reasons.append(f"queued behind {chosen[candidate.agent].key} (one active story per agent)")
                continue
            clash = next(
                (other for other in chosen.values() if any(overlaps(normalize(a), normalize(b)) for a in candidate.paths for b in other.paths)),
                None,
            )
            if clash is not None:
                candidate.status = policy.BLOCKED
                candidate.reasons.append(f"path reservations overlap {clash.key} ({clash.agent}); pausing")
                continue
            candidate.selected = True
            chosen[candidate.agent] = candidate

    return RunReport(
        generated_at=now.isoformat(),
        kickoff_window_open=kickoff_window_open(now),
        snapshot_fetched_at=snapshot.fetched_at.isoformat(),
        snapshot_source=snapshot.source,
        run_status=policy.NO_RUN if no_run else policy.READY,
        no_run_reasons=no_run,
        gate=gate,
        candidates=candidates,
    )
