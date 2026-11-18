"""Mutually exclusive file-path reservations between agents."""
from __future__ import annotations

import posixpath

from automation.coordinator.policy import AGENTS


def normalize(path: str) -> str:
    """Normalize a repository-relative path prefix. Rejects absolute paths and parent escapes."""
    raw = path.strip().replace("\\", "/")
    if not raw or raw.startswith("/") or raw.startswith("~"):
        raise ValueError(f"reservation must be a repository-relative path: {path!r}")
    trailing = raw.endswith("/")
    cleaned = posixpath.normpath(raw)
    if cleaned in {".", ""} or cleaned.startswith("..") or "/../" in f"/{cleaned}/":
        raise ValueError(f"reservation escapes the repository root: {path!r}")
    return cleaned + "/" if trailing else cleaned


def overlaps(first: str, second: str) -> bool:
    """Prefix semantics: two reservations overlap if either one is a prefix of the other."""
    return first.startswith(second) or second.startswith(first)


def owner_of(path: str) -> str | None:
    """The agent owning `path`, by longest matching owned prefix; None if no agent owns it."""
    best: tuple[int, str] | None = None
    for name, policy in AGENTS.items():
        for prefix in policy.owned_prefixes:
            if path.startswith(prefix) and (best is None or len(prefix) > best[0]):
                best = (len(prefix), name)
    return best[1] if best else None


def reservation_problems(agent: str, paths: list[str]) -> list[str]:
    """Reasons the given reservations are not allowed for `agent` (empty list = allowed)."""
    if not paths:
        return ["no file-path reservation was approved for this task"]
    problems: list[str] = []
    for raw in paths:
        try:
            path = normalize(raw)
        except ValueError as exc:
            problems.append(str(exc))
            continue
        owner = owner_of(path)
        if owner != agent:
            problems.append(f"path {path!r} is owned by {owner or 'no agent'}, not {agent}")
            continue
        for other, policy in AGENTS.items():
            if other == agent:
                continue
            for prefix in policy.owned_prefixes:
                if prefix.startswith(path) and prefix != path:
                    problems.append(f"path {path!r} contains {other}-owned territory {prefix!r}")
    return problems
