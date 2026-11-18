"""Read-only inputs: the Jira snapshot (with open PRs) and the human-approved task queue.

There is deliberately no live Jira client. Until a secure, narrowly scoped Jira integration is
verified (PE0OM-82), the coordinator only reads a snapshot file exported by a human or a read-only
tool, and refuses `--jira live` as NOT CONFIGURED.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

KEY_PATTERN = re.compile(r"^[A-Z][A-Z0-9]+-\d+$")


class InputError(ValueError):
    """An input file is missing, unreadable or malformed. Always a no-run."""


def acceptance_digest(description: str) -> str:
    normalized = "\n".join(line.rstrip() for line in (description or "").strip().splitlines())
    return "sha256:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Issue:
    key: str
    summary: str
    status: str
    labels: frozenset[str]
    description: str
    parent_key: str | None
    blocked_by: tuple[str, ...]

    @property
    def acceptance_digest(self) -> str:
        return acceptance_digest(self.description)


@dataclass(frozen=True)
class PullRequest:
    number: int
    head: str
    title: str


@dataclass(frozen=True)
class Snapshot:
    fetched_at: datetime
    issues: dict[str, Issue]
    open_prs: tuple[PullRequest, ...]
    source: str


@dataclass(frozen=True)
class QueueItem:
    key: str
    agent: str
    acceptance_digest: str
    branch: str
    paths: tuple[str, ...]


@dataclass(frozen=True)
class ApprovedQueue:
    approved_by: str
    approved_at: datetime
    items: tuple[QueueItem, ...] = field(default_factory=tuple)


def _load_json(path: Path) -> dict:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise InputError(f"file not found: {path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise InputError(f"cannot read {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise InputError(f"{path}: top-level JSON object expected")
    return data


def _parse_time(value, what: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise InputError(f"{what}: invalid ISO-8601 timestamp {value!r}") from exc
    if parsed.tzinfo is None:
        raise InputError(f"{what}: timestamp must include a timezone offset")
    return parsed


def _key(value, what: str) -> str:
    if not isinstance(value, str) or not KEY_PATTERN.match(value):
        raise InputError(f"{what}: invalid Jira key {value!r}")
    return value


def load_snapshot(path: Path) -> Snapshot:
    data = _load_json(path)
    fetched_at = _parse_time(data.get("fetched_at"), "snapshot.fetched_at")
    issues: dict[str, Issue] = {}
    for raw in data.get("issues") or []:
        key = _key(raw.get("key"), "snapshot.issues[].key")
        if key in issues:
            raise InputError(f"snapshot lists {key} twice")
        if not isinstance(raw.get("status"), str):
            raise InputError(f"{key}: status missing")
        issues[key] = Issue(
            key=key,
            summary=str(raw.get("summary") or ""),
            status=raw["status"],
            labels=frozenset(str(label) for label in raw.get("labels") or []),
            description=str(raw.get("description") or ""),
            parent_key=raw.get("parent"),
            blocked_by=tuple(_key(item, f"{key}.blocked_by") for item in raw.get("blocked_by") or []),
        )
    prs = tuple(
        PullRequest(number=int(pr["number"]), head=str(pr.get("head") or ""), title=str(pr.get("title") or ""))
        for pr in data.get("open_prs") or []
    )
    if "open_prs" not in data:
        raise InputError("snapshot.open_prs is required (use [] when there are none)")
    return Snapshot(fetched_at=fetched_at, issues=issues, open_prs=prs, source=str(data.get("source") or "unknown"))


def load_queue(path: Path) -> ApprovedQueue:
    data = _load_json(path)
    approved_by = str(data.get("approved_by") or "").strip()
    if not approved_by:
        raise InputError("queue.approved_by is required: the queue must be human-approved")
    items = []
    seen: set[str] = set()
    for raw in data.get("items") or []:
        key = _key(raw.get("key"), "queue.items[].key")
        if key in seen:
            raise InputError(f"queue lists {key} twice")
        seen.add(key)
        digest = str(raw.get("acceptance_digest") or "")
        if not digest.startswith("sha256:"):
            raise InputError(f"{key}: acceptance_digest (sha256) is required")
        items.append(
            QueueItem(
                key=key,
                agent=str(raw.get("agent") or ""),
                acceptance_digest=digest,
                branch=str(raw.get("branch") or ""),
                paths=tuple(str(p) for p in raw.get("paths") or []),
            )
        )
    return ApprovedQueue(approved_by=approved_by, approved_at=_parse_time(data.get("approved_at"), "queue.approved_at"), items=tuple(items))
