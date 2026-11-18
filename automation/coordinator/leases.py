"""Atomic task leases in a local SQLite store.

Guarantees, enforced twice (in the claim transaction and by partial unique indexes):
- one active lease per Jira issue;
- one active lease per agent;
- no overlapping file-path reservations between active leases.
Every claim, refusal, expiry, start and release is written to an append-only event table.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from automation.coordinator.ownership import normalize, overlaps

ACTIVE_STATES = ("claimed", "started")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS leases (
    lease_id TEXT PRIMARY KEY,
    issue_key TEXT NOT NULL,
    agent TEXT NOT NULL,
    branch TEXT NOT NULL,
    worktree TEXT NOT NULL,
    paths TEXT NOT NULL,
    state TEXT NOT NULL,
    claimed_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    session_id TEXT,
    ended_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS one_active_lease_per_issue ON leases(issue_key) WHERE state IN ('claimed', 'started');
CREATE UNIQUE INDEX IF NOT EXISTS one_active_lease_per_agent ON leases(agent) WHERE state IN ('claimed', 'started');
CREATE UNIQUE INDEX IF NOT EXISTS one_active_lease_per_worktree ON leases(worktree) WHERE state IN ('claimed', 'started');
CREATE TABLE IF NOT EXISTS lease_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT NOT NULL,
    lease_id TEXT,
    issue_key TEXT NOT NULL,
    agent TEXT NOT NULL,
    event TEXT NOT NULL,
    detail TEXT
);
"""


@dataclass(frozen=True)
class Lease:
    lease_id: str
    issue_key: str
    agent: str
    branch: str
    worktree: str
    paths: tuple[str, ...]
    state: str
    claimed_at: str
    expires_at: str
    session_id: str | None


@dataclass(frozen=True)
class ClaimResult:
    claimed: bool
    lease: Lease | None
    reason: str


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _row_to_lease(row) -> Lease:
    return Lease(row[0], row[1], row[2], row[3], row[4], tuple(json.loads(row[5])), row[6], row[7], row[8], row[9])


_LEASE_COLUMNS = "lease_id, issue_key, agent, branch, worktree, paths, state, claimed_at, expires_at, session_id"


class LeaseStore:
    def __init__(self, path: Path, clock: Callable[[], datetime] = _utc_now):
        self.path = Path(path)
        self.clock = clock

    def _now(self) -> datetime:
        """Always UTC, so ISO strings compare correctly in SQL."""
        return self.clock().astimezone(timezone.utc)

    # -- connections -----------------------------------------------------------------------
    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        conn.executescript(_SCHEMA)
        return conn

    @staticmethod
    def read_only_active(path: Path) -> list[Lease]:
        """Active leases without creating or modifying anything (used by dry-run previews)."""
        if not Path(path).exists():
            return []
        with closing(sqlite3.connect(f"file:{Path(path)}?mode=ro", uri=True)) as conn:
            rows = conn.execute(f"SELECT {_LEASE_COLUMNS} FROM leases WHERE state IN ('claimed', 'started')").fetchall()
        return [_row_to_lease(row) for row in rows]

    # -- helpers inside a transaction ------------------------------------------------------
    def _event(self, conn, lease_id, issue_key, agent, event, detail="") -> None:
        conn.execute(
            "INSERT INTO lease_events (at, lease_id, issue_key, agent, event, detail) VALUES (?, ?, ?, ?, ?, ?)",
            (self._now().isoformat(), lease_id, issue_key, agent, event, detail),
        )

    def _expire_stale(self, conn) -> None:
        now = self._now().isoformat()
        stale = conn.execute(
            f"SELECT {_LEASE_COLUMNS} FROM leases WHERE state IN ('claimed', 'started') AND expires_at <= ?", (now,)
        ).fetchall()
        for row in stale:
            lease = _row_to_lease(row)
            conn.execute("UPDATE leases SET state = 'expired', ended_at = ? WHERE lease_id = ?", (now, lease.lease_id))
            self._event(conn, lease.lease_id, lease.issue_key, lease.agent, "expired", f"lease expired at {lease.expires_at}")

    def _active(self, conn) -> list[Lease]:
        rows = conn.execute(f"SELECT {_LEASE_COLUMNS} FROM leases WHERE state IN ('claimed', 'started')").fetchall()
        return [_row_to_lease(row) for row in rows]

    # -- public API ------------------------------------------------------------------------
    def claim(self, issue_key: str, agent: str, branch: str, worktree: str, paths: list[str], ttl: timedelta) -> ClaimResult:
        normalized = [normalize(p) for p in paths]
        with closing(self._connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")  # serializes all claimers on this store
            try:
                self._expire_stale(conn)
                reason = self._conflict(conn, issue_key, agent, worktree, normalized)
                if reason:
                    self._event(conn, None, issue_key, agent, "claim_refused", reason)
                    conn.execute("COMMIT")
                    return ClaimResult(False, None, reason)
                now = self._now()
                lease = Lease(
                    lease_id=str(uuid.uuid4()),
                    issue_key=issue_key,
                    agent=agent,
                    branch=branch,
                    worktree=worktree,
                    paths=tuple(normalized),
                    state="claimed",
                    claimed_at=now.isoformat(),
                    expires_at=(now + ttl).isoformat(),
                    session_id=None,
                )
                conn.execute(
                    f"INSERT INTO leases ({_LEASE_COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (lease.lease_id, issue_key, agent, branch, worktree, json.dumps(lease.paths), "claimed", lease.claimed_at, lease.expires_at, None),
                )
                self._event(conn, lease.lease_id, issue_key, agent, "claimed", f"expires {lease.expires_at}; paths {list(lease.paths)}")
                conn.execute("COMMIT")
            except sqlite3.IntegrityError as exc:
                conn.execute("ROLLBACK")
                return ClaimResult(False, None, f"concurrent claim rejected by database constraint: {exc}")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
        # Read back outside the transaction: the claim only counts if the store still says it is ours.
        if not self.verify(lease.lease_id, issue_key, agent):
            return ClaimResult(False, None, "post-claim verification failed: lease is not held by this claimer")
        return ClaimResult(True, lease, "claimed")

    def _conflict(self, conn, issue_key, agent, worktree, paths) -> str:
        for lease in self._active(conn):
            if lease.issue_key == issue_key:
                return f"{issue_key} is already leased to {lease.agent} until {lease.expires_at}"
            if lease.agent == agent:
                return f"{agent} already has an active story ({lease.issue_key}); one active story per agent"
            if lease.worktree == worktree:
                return f"worktree {worktree} is already used by {lease.issue_key}"
            for mine in paths:
                for theirs in lease.paths:
                    if overlaps(mine, theirs):
                        return f"path reservation {mine!r} overlaps {theirs!r} held by {lease.agent} ({lease.issue_key}); pausing"
        return ""

    def verify(self, lease_id: str, issue_key: str, agent: str) -> bool:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT lease_id, agent FROM leases WHERE issue_key = ? AND state IN ('claimed', 'started')", (issue_key,)
            ).fetchone()
        return row is not None and row[0] == lease_id and row[1] == agent

    def mark_started(self, lease_id: str, session_id: str) -> Lease:
        if not session_id.strip():
            raise ValueError("a session id is required to mark a task as actually started")
        with closing(self._connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            self._expire_stale(conn)
            row = conn.execute(f"SELECT {_LEASE_COLUMNS} FROM leases WHERE lease_id = ?", (lease_id,)).fetchone()
            if row is None or row[6] != "claimed":
                conn.execute("COMMIT")
                raise ValueError(f"lease {lease_id} is not in the claimed state")
            conn.execute("UPDATE leases SET state = 'started', session_id = ? WHERE lease_id = ?", (session_id, lease_id))
            self._event(conn, lease_id, row[1], row[2], "started", f"session {session_id}")
            conn.execute("COMMIT")
            row = conn.execute(f"SELECT {_LEASE_COLUMNS} FROM leases WHERE lease_id = ?", (lease_id,)).fetchone()
        return _row_to_lease(row)

    def release(self, lease_id: str, reason: str) -> None:
        with closing(self._connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT issue_key, agent, state FROM leases WHERE lease_id = ?", (lease_id,)).fetchone()
            if row is None or row[2] not in ACTIVE_STATES:
                conn.execute("COMMIT")
                raise ValueError(f"lease {lease_id} is not active")
            conn.execute("UPDATE leases SET state = 'released', ended_at = ? WHERE lease_id = ?", (self._now().isoformat(), lease_id))
            self._event(conn, lease_id, row[0], row[1], "released", reason)
            conn.execute("COMMIT")

    def active(self) -> list[Lease]:
        with closing(self._connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            self._expire_stale(conn)
            conn.execute("COMMIT")
            return self._active(conn)

    def events(self) -> list[tuple]:
        with closing(self._connect()) as conn:
            return conn.execute("SELECT at, lease_id, issue_key, agent, event, detail FROM lease_events ORDER BY event_id").fetchall()
