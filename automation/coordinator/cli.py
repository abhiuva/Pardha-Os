"""PE0OM-82 coordinator CLI. Dry-run is the default for every command that could change state.

Exit codes: 0 ready/ok, 1 error, 2 no-run or nothing claimable, 3 not configured.
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from automation.coordinator import policy
from automation.coordinator.gitstate import GitState
from automation.coordinator.leases import LeaseStore
from automation.coordinator.planner import KOLKATA, RunReport, evaluate, owner_agents
from automation.coordinator.sources import InputError, load_queue, load_snapshot

EXIT_OK, EXIT_ERROR, EXIT_NO_RUN, EXIT_NOT_CONFIGURED = 0, 1, 2, 3
DEFAULT_STATE_DIR = Path.home() / ".pardha-coordinator"
LAUNCH_HINT = {"claude": "claude", "codex": "codex"}


def _print(payload) -> None:
    print(json.dumps(payload, indent=2, default=str))


def _log_entry(report: RunReport, mode: str, run_id: str, claims: dict[str, dict]) -> dict:
    now_local = datetime.fromisoformat(report.generated_at).astimezone(KOLKATA)
    return {
        "run_id": run_id,
        "date": now_local.date().isoformat(),
        "time": now_local.strftime("%H:%M:%S %Z"),
        "mode": mode,
        "run_status": report.run_status,
        "no_run_reasons": report.no_run_reasons,
        "kickoff_window_open": report.kickoff_window_open,
        "snapshot_fetched_at": report.snapshot_fetched_at,
        "readiness_gate": report.gate,
        "entries": [
            {
                "key": c.key,
                "agent_role": c.agent,
                "parent_epic": c.parent,
                "approved": c.approved,
                "status": claims.get(c.key, {}).get("status", c.status),
                "selected": c.selected,
                "blockers": c.reasons,
                "open_prs": c.open_prs,
                "lease_id": claims.get(c.key, {}).get("lease_id"),
                "session_id": None,
                "branch": c.branch,
                "worktree": c.worktree,
            }
            for c in report.candidates
        ],
    }


def _append_log(path: Path | None, entry: dict) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, default=str) + "\n")


def _report(args) -> RunReport:
    snapshot = load_snapshot(Path(args.snapshot))
    queue = load_queue(Path(args.queue)) if args.queue else None
    active = LeaseStore.read_only_active(Path(args.state_dir) / "leases.db")
    return evaluate(snapshot, queue, GitState(Path(args.repo)), active, Path(args.worktree_root))


def cmd_preview(args) -> int:
    report = _report(args)
    entry = _log_entry(report, "dry-run", str(uuid.uuid4()), {})
    _append_log(Path(args.log_file) if args.log_file else None, entry)
    _print(entry)
    return EXIT_OK if report.run_status == policy.READY and report.selected else EXIT_NO_RUN


def cmd_claim(args) -> int:
    report = _report(args)
    run_id = str(uuid.uuid4())
    if not args.execute:
        entry = _log_entry(report, "dry-run", run_id, {})
        entry["would_claim"] = [c.key for c in report.selected]
        _append_log(Path(args.log_file) if args.log_file else None, entry)
        _print(entry)
        return EXIT_OK if report.run_status == policy.READY and report.selected else EXIT_NO_RUN

    state_dir = Path(args.state_dir)
    log_file = Path(args.log_file) if args.log_file else state_dir / "kickoff-log.jsonl"
    if report.run_status != policy.READY or not report.selected:
        entry = _log_entry(report, "execute", run_id, {})
        _append_log(log_file, entry)
        _print(entry)
        return EXIT_NO_RUN

    store = LeaseStore(state_dir / "leases.db")
    git = GitState(Path(args.repo))
    claims: dict[str, dict] = {}
    for candidate in report.selected:
        ttl = policy.AGENTS[candidate.agent].budget_minutes
        result = store.claim(candidate.key, candidate.agent, candidate.branch, candidate.worktree, candidate.paths, timedelta(minutes=ttl))
        if not result.claimed:
            claims[candidate.key] = {"status": policy.BLOCKED, "reason": result.reason}
            candidate.reasons.append(result.reason)
            continue
        try:
            git.create_worktree(candidate.worktree, candidate.branch, args.base)
        except Exception as exc:  # never leave a lease without its isolated worktree
            store.release(result.lease.lease_id, f"worktree creation failed: {exc}")
            claims[candidate.key] = {"status": policy.BLOCKED, "reason": str(exc)}
            candidate.reasons.append(f"worktree creation failed: {exc}")
            continue
        claims[candidate.key] = {
            "status": policy.CLAIMED,
            "lease_id": result.lease.lease_id,
            "expires_at": result.lease.expires_at,
            "manual_launch": f"cd {candidate.worktree} && {LAUNCH_HINT[candidate.agent]}",
            "after_launch": f"python -m automation.coordinator mark-started --lease-id {result.lease.lease_id} --session-id <SESSION_ID>",
        }
    entry = _log_entry(report, "execute", run_id, claims)
    entry["claims"] = claims
    _append_log(log_file, entry)
    _print(entry)
    return EXIT_OK if any(c["status"] == policy.CLAIMED for c in claims.values()) else EXIT_NO_RUN


def cmd_approve(args) -> int:
    """Manual fallback: a human pastes ready keys; the coordinator records them with the current
    acceptance-criteria digest so later changes in Jira are detected."""
    out = Path(args.out)
    if out.exists():
        print(f"refusing to overwrite existing queue file {out}", file=sys.stderr)
        return EXIT_ERROR
    snapshot = load_snapshot(Path(args.snapshot))
    items = []
    for spec in args.item:
        key, _, path_spec = spec.partition(":")
        issue = snapshot.issues.get(key)
        if issue is None:
            print(f"{key} is not in the Jira snapshot", file=sys.stderr)
            return EXIT_ERROR
        owners = owner_agents(issue)
        if len(owners) != 1:
            print(f"{key} needs exactly one owner label, found {owners or 'none'}", file=sys.stderr)
            return EXIT_ERROR
        agent = owners[0]
        slug = "-".join("".join(ch if ch.isalnum() else " " for ch in issue.summary.lower()).split()[:4]) or "task"
        prefix = "feature/" if agent == "claude" else "codex/"
        items.append({
            "key": key,
            "agent": agent,
            "acceptance_digest": issue.acceptance_digest,
            "branch": f"{prefix}{key}-{slug}",
            "paths": [p for p in path_spec.split(",") if p],
        })
    queue = {"approved_by": args.approved_by, "approved_at": datetime.now(timezone.utc).isoformat(), "items": items}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(queue, indent=2) + "\n", encoding="utf-8")
    _print(queue)
    return EXIT_OK


def cmd_mark_started(args) -> int:
    lease = LeaseStore(Path(args.state_dir) / "leases.db").mark_started(args.lease_id, args.session_id)
    _append_log(Path(args.log_file) if args.log_file else Path(args.state_dir) / "kickoff-log.jsonl", {
        "event": "started", "status": policy.ACTUALLY_STARTED, "key": lease.issue_key, "agent_role": lease.agent,
        "lease_id": lease.lease_id, "session_id": lease.session_id, "at": datetime.now(timezone.utc).isoformat(),
    })
    _print({"status": policy.ACTUALLY_STARTED, **asdict(lease)})
    return EXIT_OK


def cmd_release(args) -> int:
    LeaseStore(Path(args.state_dir) / "leases.db").release(args.lease_id, args.reason)
    _print({"released": args.lease_id, "reason": args.reason})
    return EXIT_OK


def cmd_status(args) -> int:
    store = LeaseStore(Path(args.state_dir) / "leases.db")
    _print({"active": [asdict(lease) for lease in store.active()], "events": store.events()})
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m automation.coordinator", description=__doc__)
    parser.add_argument("--state-dir", default=str(DEFAULT_STATE_DIR), help="local lease store and kickoff log directory")
    parser.add_argument("--jira", choices=["snapshot", "live"], default="snapshot", help="live Jira is NOT CONFIGURED until a secure integration is verified")
    sub = parser.add_subparsers(dest="command")

    def plan_args(p):
        p.add_argument("--snapshot", required=True, help="Jira + open-PR snapshot JSON (read-only export)")
        p.add_argument("--queue", help="human-approved task queue JSON")
        p.add_argument("--repo", default=".", help="repository whose worktrees and branches are inspected")
        p.add_argument("--worktree-root", required=True, help="directory under which new task worktrees are created")
        p.add_argument("--log-file", help="append the kickoff log entry to this JSONL file")

    preview = sub.add_parser("preview", help="read-only readiness preview (default)")
    plan_args(preview)
    preview.set_defaults(func=cmd_preview)

    claim = sub.add_parser("claim", help="claim selected tasks; dry-run unless --execute")
    plan_args(claim)
    claim.add_argument("--execute", action="store_true", help="actually take leases and create worktrees")
    claim.add_argument("--base", default="origin/develop", help="base ref for new task branches")
    claim.set_defaults(func=cmd_claim)

    approve = sub.add_parser("approve", help="manual fallback: write an approved queue from pasted keys")
    approve.add_argument("--snapshot", required=True)
    approve.add_argument("--item", action="append", required=True, metavar="KEY:path1,path2", help="Jira key and its file-path reservations")
    approve.add_argument("--approved-by", required=True)
    approve.add_argument("--out", required=True)
    approve.set_defaults(func=cmd_approve)

    started = sub.add_parser("mark-started", help="record that a human launched the agent session")
    started.add_argument("--lease-id", required=True)
    started.add_argument("--session-id", required=True)
    started.add_argument("--log-file")
    started.set_defaults(func=cmd_mark_started)

    release = sub.add_parser("release", help="release an active lease")
    release.add_argument("--lease-id", required=True)
    release.add_argument("--reason", required=True)
    release.set_defaults(func=cmd_release)

    status = sub.add_parser("status", help="active leases and the lease event log")
    status.set_defaults(func=cmd_status)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.jira == "live":
        _print({"run_status": policy.NOT_CONFIGURED, "reason": "live Jira access is not configured: no verified, narrowly scoped coordinator credentials (PE0OM-82). Use a snapshot."})
        return EXIT_NOT_CONFIGURED
    if args.command is None:
        parser.print_help()
        return EXIT_NO_RUN
    try:
        return args.func(args)
    except InputError as exc:
        _print({"run_status": policy.NO_RUN, "no_run_reasons": [str(exc)]})
        return EXIT_NO_RUN
    except (ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
