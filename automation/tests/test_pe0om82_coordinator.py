"""PE0OM-82 coordinator tests. Isolated: temporary directories, a throwaway git repository,
no network (socket connections fail), no Jira, no GitHub, no agent launch."""
from __future__ import annotations

import contextlib
import io
import json
import socket
import subprocess
import tempfile
import threading
import unittest
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from automation.coordinator import cli, policy
from automation.coordinator.gitstate import GitState
from automation.coordinator.leases import LeaseStore
from automation.coordinator.ownership import reservation_problems
from automation.coordinator.planner import evaluate
from automation.coordinator.sources import InputError, acceptance_digest, load_queue, load_snapshot

NOW = datetime(2026, 11, 18, 3, 5, tzinfo=timezone.utc)  # 08:35 Asia/Kolkata, a Wednesday
AC = "Goal: x.\n\n**Acceptance criteria:** do the thing safely."


def _no_network(*_args, **_kwargs):
    raise AssertionError("network access attempted during an isolated coordinator test")


def issue(key, *, status="To Do", labels=("pardha-v1-dec7", "ai-ready", "ai-owner-claude"), description=AC, blocked_by=(), parent="PE0OM-35"):
    return {"key": key, "summary": f"Summary of {key}", "status": status, "labels": list(labels), "description": description, "parent": parent, "blocked_by": list(blocked_by)}


def gate_issues():
    return [issue(key, status="In Review", labels=()) for key in policy.READINESS_GATE_KEYS]


def write_json(path: Path, data) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def claim_in_process(db_path: str, agent: str, worktree: str) -> bool:
    store = LeaseStore(Path(db_path))
    return store.claim("PE0OM-500", agent, f"feature/PE0OM-500-{agent}", worktree, [f"automation/{agent}/"], timedelta(minutes=5)).claimed


def claim_overlap_in_process(db_path: str, agent: str, key: str, worktree: str) -> str:
    """Different issue and agent, overlapping paths; the conflict check is slowed down so that
    concurrent claimers are inside the check at the same time."""
    import time

    original = LeaseStore._conflict

    def slow_conflict(self, *args):
        reason = original(self, *args)
        time.sleep(0.3)
        return reason

    LeaseStore._conflict = slow_conflict
    try:
        result = LeaseStore(Path(db_path)).claim(key, agent, f"feature/{key}-x", worktree, ["automation/shared/"], timedelta(minutes=5))
        return "claimed" if result.claimed else "refused"
    except Exception as exc:  # an error is a failure of the atomic-claim guarantee, not a clean refusal
        return f"error: {exc}"


class _Base(unittest.TestCase):
    def setUp(self):
        self.net = mock.patch.object(socket.socket, "connect", _no_network)
        self.net.start()
        self.addCleanup(self.net.stop)
        self.tmp = Path(tempfile.mkdtemp(prefix="pe0om82-"))
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        for args in (["init", "-q", "-b", "main"], ["config", "user.email", "test@example.invalid"], ["config", "user.name", "test"], ["commit", "-q", "--allow-empty", "-m", "base"]):
            subprocess.run(["git", *args], cwd=self.repo, check=True, capture_output=True)
        self.worktrees = self.tmp / "worktrees"
        self.state = self.tmp / "state"
        self.git = GitState(self.repo)

    def snapshot(self, issues, prs=(), fetched_at=None):
        data = {"fetched_at": (fetched_at or NOW - timedelta(minutes=5)).isoformat(), "source": "test", "issues": gate_issues() + list(issues), "open_prs": list(prs)}
        return load_snapshot(write_json(self.tmp / "snapshot.json", data))

    def queue(self, *items):
        data = {"approved_by": "Product Owner (test)", "approved_at": NOW.isoformat(), "items": list(items)}
        return load_queue(write_json(self.tmp / "queue.json", data))

    @staticmethod
    def item(key, agent="claude", paths=("automation/x/",), description=AC, branch=None):
        prefix = "feature/" if agent == "claude" else "codex/"
        return {"key": key, "agent": agent, "acceptance_digest": acceptance_digest(description), "branch": branch or f"{prefix}{key}-task", "paths": list(paths)}

    def run_eval(self, snapshot, queue, leases=()):
        return evaluate(snapshot, queue, self.git, list(leases), self.worktrees, now=NOW)

    def candidate(self, report, key):
        return next(c for c in report.candidates if c.key == key)


class ReadinessRulesTestCase(_Base):
    def test_clean_approved_story_is_ready_and_selected(self):
        report = self.run_eval(self.snapshot([issue("PE0OM-500")]), self.queue(self.item("PE0OM-500")))
        self.assertEqual(report.run_status, policy.READY, report.no_run_reasons)
        candidate = self.candidate(report, "PE0OM-500")
        self.assertEqual((candidate.status, candidate.selected), (policy.READY, True), candidate.reasons)

    def test_excluded_labels_and_missing_ready_or_owner_block(self):
        cases = {
            "PE0OM-501": ("pardha-v1-dec7", "ai-ready", "ai-owner-claude", "ai-blocked"),
            "PE0OM-502": ("pardha-v1-dec7", "ai-ready", "ai-owner-claude", "ai-pr-review"),
            "PE0OM-503": ("pardha-v1-dec7", "ai-ready", "ai-owner-claude", "v1-deferred"),
            "PE0OM-504": ("pardha-v1-dec7", "ai-owner-claude"),
            "PE0OM-505": ("pardha-v1-dec7", "ai-ready", "ai-owner-claude", "ai-owner-codex"),
        }
        snapshot = self.snapshot([issue(key, labels=labels) for key, labels in cases.items()])
        report = self.run_eval(snapshot, self.queue(*[self.item(key, paths=(f"automation/{key}/",)) for key in cases]))
        for key in cases:
            with self.subTest(key=key):
                candidate = self.candidate(report, key)
                self.assertEqual(candidate.status, policy.BLOCKED)
                self.assertFalse(candidate.selected)

    def test_status_must_be_to_do_and_acceptance_criteria_required(self):
        snapshot = self.snapshot([issue("PE0OM-510", status="In Progress"), issue("PE0OM-511", description="Just do it.")])
        report = self.run_eval(snapshot, self.queue(self.item("PE0OM-510", paths=("automation/a/",)), self.item("PE0OM-511", paths=("automation/b/",), description="Just do it.")))
        self.assertIn("status is 'In Progress'", " ".join(self.candidate(report, "PE0OM-510").reasons))
        self.assertIn("no acceptance criteria", " ".join(self.candidate(report, "PE0OM-511").reasons))

    def test_unfinished_dependency_blocks_but_ambiguous_dependency_is_a_no_run(self):
        snapshot = self.snapshot([issue("PE0OM-520", blocked_by=("PE0OM-75",)), issue("PE0OM-521", blocked_by=("PE0OM-999",))])
        blocked = self.run_eval(snapshot, self.queue(self.item("PE0OM-520")))
        self.assertEqual(blocked.run_status, policy.READY)
        self.assertIn("blocked by PE0OM-75", " ".join(self.candidate(blocked, "PE0OM-520").reasons))
        ambiguous = self.run_eval(snapshot, self.queue(self.item("PE0OM-521")))
        self.assertEqual(ambiguous.run_status, policy.NO_RUN)
        self.assertIn("ambiguous dependency", " ".join(ambiguous.no_run_reasons))
        self.assertFalse(ambiguous.selected)

    def test_open_pull_request_for_the_issue_blocks(self):
        snapshot = self.snapshot([issue("PE0OM-530")], prs=[{"number": 42, "head": "feature/PE0OM-530-x", "title": "x"}])
        candidate = self.candidate(self.run_eval(snapshot, self.queue(self.item("PE0OM-530"))), "PE0OM-530")
        self.assertEqual(candidate.status, policy.BLOCKED)
        self.assertEqual(candidate.open_prs, [42])

    def test_allowlisted_key_without_scope_label_is_allowed_but_unapproved_issue_is_not_selected(self):
        snapshot = self.snapshot([issue("PE0OM-540", labels=("pardha-mvp-new", "ai-ready", "ai-owner-claude")), issue("PE0OM-541")])
        report = self.run_eval(snapshot, self.queue(self.item("PE0OM-540")))
        self.assertTrue(self.candidate(report, "PE0OM-540").selected)
        unapproved = self.candidate(report, "PE0OM-541")
        self.assertFalse(unapproved.selected)
        self.assertIn("not in the human-approved queue", unapproved.reasons)


class NoRunConditionsTestCase(_Base):
    def test_stale_or_future_snapshot_is_a_no_run(self):
        for fetched in (NOW - timedelta(minutes=31), NOW + timedelta(minutes=10)):
            with self.subTest(fetched=fetched):
                report = self.run_eval(self.snapshot([issue("PE0OM-550")], fetched_at=fetched), self.queue(self.item("PE0OM-550")))
                self.assertEqual(report.run_status, policy.NO_RUN)
                self.assertFalse(report.selected)

    def test_missing_readiness_gate_issue_is_a_no_run(self):
        data = {"fetched_at": NOW.isoformat(), "issues": [issue("PE0OM-551")], "open_prs": []}
        report = self.run_eval(load_snapshot(write_json(self.tmp / "s.json", data)), self.queue(self.item("PE0OM-551")))
        self.assertEqual(report.run_status, policy.NO_RUN)
        self.assertIn("PE0OM-93", " ".join(report.no_run_reasons))

    def test_changed_acceptance_criteria_is_a_no_run(self):
        snapshot = self.snapshot([issue("PE0OM-552", description=AC + "\nNew requirement added later.")])
        report = self.run_eval(snapshot, self.queue(self.item("PE0OM-552")))
        self.assertEqual(report.run_status, policy.NO_RUN)
        self.assertIn("acceptance criteria changed", " ".join(report.no_run_reasons))

    def test_missing_queue_is_preview_only(self):
        report = self.run_eval(self.snapshot([issue("PE0OM-553")]), None)
        self.assertEqual(report.run_status, policy.NO_RUN)
        self.assertFalse(report.selected)

    def test_malformed_inputs_are_rejected(self):
        with self.assertRaises(InputError):
            load_snapshot(self.tmp / "missing.json")
        with self.assertRaises(InputError):
            load_snapshot(write_json(self.tmp / "naive.json", {"fetched_at": "2026-11-18T08:00:00", "issues": [], "open_prs": []}))
        with self.assertRaises(InputError):
            load_snapshot(write_json(self.tmp / "noprs.json", {"fetched_at": NOW.isoformat(), "issues": []}))
        with self.assertRaises(InputError):
            load_queue(write_json(self.tmp / "q.json", {"approved_at": NOW.isoformat(), "items": []}))


class OwnershipAndBranchTestCase(_Base):
    def test_path_reservations_follow_exclusive_ownership(self):
        self.assertEqual(reservation_problems("claude", ["pardha-core/app/auth/", "pardha-core/tests/test_pe0om76_"]), [])
        self.assertEqual(reservation_problems("codex", ["pardha-core/dashboard/src/ceo-console/", "pardha-core/tests/test_adversarial_auth.py"]), [])
        self.assertTrue(reservation_problems("codex", ["pardha-core/app/"]))
        self.assertTrue(reservation_problems("claude", ["pardha-core/dashboard/"]))
        self.assertTrue(reservation_problems("claude", ["pardha-core/"]))  # would swallow Codex territory
        self.assertTrue(reservation_problems("claude", ["CLAUDE.md"]))  # unowned: needs PO
        self.assertTrue(reservation_problems("claude", ["../outside/"]))
        self.assertTrue(reservation_problems("claude", []))

    def test_protected_existing_or_unnamed_branches_block(self):
        subprocess.run(["git", "branch", "feature/PE0OM-561-task"], cwd=self.repo, check=True)
        snapshot = self.snapshot([issue("PE0OM-560"), issue("PE0OM-561"), issue("PE0OM-562")])
        report = self.run_eval(snapshot, self.queue(
            self.item("PE0OM-560", paths=("automation/a/",), branch="develop"),
            self.item("PE0OM-561", paths=("automation/b/",)),
            self.item("PE0OM-562", paths=("automation/c/",), branch="feature/other-task"),
        ))
        self.assertIn("protected", " ".join(self.candidate(report, "PE0OM-560").reasons))
        self.assertIn("already exists", " ".join(self.candidate(report, "PE0OM-561").reasons))
        self.assertIn("does not name PE0OM-562", " ".join(self.candidate(report, "PE0OM-562").reasons))

    def test_existing_branch_for_the_issue_under_another_name_blocks(self):
        subprocess.run(["git", "branch", "feature/PE0OM-563-earlier-attempt"], cwd=self.repo, check=True)
        subprocess.run(["git", "branch", "feature/PE0OM-5630-unrelated"], cwd=self.repo, check=True)
        snapshot = self.snapshot([issue("PE0OM-563"), issue("PE0OM-564")], prs=[{"number": 7, "head": "feature/PE0OM-5640-x", "title": "PE0OM-5640 other"}])
        report = self.run_eval(snapshot, self.queue(self.item("PE0OM-563", paths=("automation/a/",)), self.item("PE0OM-564", paths=("automation/b/",))))
        self.assertIn("feature/PE0OM-563-earlier-attempt", " ".join(self.candidate(report, "PE0OM-563").reasons))
        self.assertNotIn("PE0OM-5630", " ".join(self.candidate(report, "PE0OM-563").reasons))
        self.assertEqual(self.candidate(report, "PE0OM-564").open_prs, [])  # PE0OM-5640 is a different issue

    def test_one_story_per_agent_and_both_agents_selected_when_disjoint(self):
        snapshot = self.snapshot([
            issue("PE0OM-570"),
            issue("PE0OM-571"),
            issue("PE0OM-572", labels=("pardha-v1-dec7", "ai-ready", "ai-owner-codex")),
        ])
        report = self.run_eval(snapshot, self.queue(
            self.item("PE0OM-570", paths=("automation/a/",)),
            self.item("PE0OM-571", paths=("automation/b/",)),
            self.item("PE0OM-572", agent="codex", paths=("pardha-core/dashboard/src/x/",)),
        ))
        self.assertEqual(sorted(c.key for c in report.selected), ["PE0OM-570", "PE0OM-572"])
        self.assertIn("queued behind PE0OM-570", " ".join(self.candidate(report, "PE0OM-571").reasons))
        self.assertNotEqual(self.candidate(report, "PE0OM-570").worktree, self.candidate(report, "PE0OM-572").worktree)


class LeaseTestCase(_Base):
    def store(self, clock=lambda: NOW):
        return LeaseStore(self.state / "leases.db", clock=clock)

    def test_concurrent_processes_claim_the_same_issue_exactly_once(self):
        db = str(self.state / "leases.db")
        LeaseStore(Path(db))._connect().close()
        with ProcessPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(claim_in_process, [db] * 6, [f"agent{i}" for i in range(6)], [str(self.tmp / f"wt{i}") for i in range(6)]))
        self.assertEqual(results.count(True), 1, results)
        self.assertEqual(len(LeaseStore(Path(db)).active()), 1)

    def test_concurrent_overlapping_reservations_are_serialized_cleanly(self):
        db = str(self.state / "leases.db")
        LeaseStore(Path(db))._connect().close()
        with ProcessPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(
                claim_overlap_in_process,
                [db] * 4,
                ["claude", "codex", "agent3", "agent4"],
                [f"PE0OM-51{n}" for n in range(4)],
                [str(self.tmp / f"ov{n}") for n in range(4)],
            ))
        self.assertEqual(results.count("claimed"), 1, results)
        self.assertEqual(results.count("refused"), 3, results)

    def test_concurrent_threads_for_one_agent_get_one_story(self):
        store = self.store()
        results: list[bool] = []
        lock = threading.Lock()

        def claim(n):
            outcome = store.claim(f"PE0OM-58{n}", "claude", f"feature/PE0OM-58{n}-x", str(self.tmp / f"w{n}"), [f"automation/t{n}/"], timedelta(minutes=5))
            with lock:
                results.append(outcome.claimed)

        threads = [threading.Thread(target=claim, args=(n,)) for n in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(results.count(True), 1, results)

    def test_overlapping_paths_pause_the_second_claim(self):
        store = self.store()
        self.assertTrue(store.claim("PE0OM-590", "claude", "feature/PE0OM-590-x", "/w/a", ["automation/shared/"], timedelta(minutes=5)).claimed)
        refused = store.claim("PE0OM-591", "codex", "codex/PE0OM-591-x", "/w/b", ["automation/shared/sub/"], timedelta(minutes=5))
        self.assertFalse(refused.claimed)
        self.assertIn("overlaps", refused.reason)
        self.assertIn("claim_refused", [event[4] for event in store.events()])

    def test_expired_lease_is_logged_and_reclaimable(self):
        clock = {"now": NOW}
        store = self.store(lambda: clock["now"])
        first = store.claim("PE0OM-600", "claude", "feature/PE0OM-600-x", "/w/a", ["automation/a/"], timedelta(minutes=10))
        self.assertTrue(first.claimed)
        self.assertFalse(store.claim("PE0OM-600", "codex", "codex/PE0OM-600-x", "/w/b", ["pardha-core/dashboard/"], timedelta(minutes=10)).claimed)
        clock["now"] = NOW + timedelta(minutes=11)
        second = store.claim("PE0OM-600", "codex", "codex/PE0OM-600-x", "/w/b", ["pardha-core/dashboard/"], timedelta(minutes=10))
        self.assertTrue(second.claimed)
        events = [event[4] for event in store.events()]
        self.assertEqual(events, ["claimed", "claim_refused", "expired", "claimed"])

    def test_database_constraints_hold_even_if_the_conflict_check_is_bypassed(self):
        store = self.store()
        store.claim("PE0OM-610", "claude", "feature/PE0OM-610-x", "/w/a", ["automation/a/"], timedelta(minutes=5))
        with mock.patch.object(LeaseStore, "_conflict", return_value=""):
            again = store.claim("PE0OM-610", "codex", "codex/PE0OM-610-x", "/w/b", ["pardha-core/dashboard/"], timedelta(minutes=5))
        self.assertFalse(again.claimed)
        self.assertIn("constraint", again.reason)

    def test_started_requires_a_session_id_and_release_ends_the_lease(self):
        store = self.store()
        lease = store.claim("PE0OM-620", "claude", "feature/PE0OM-620-x", "/w/a", ["automation/a/"], timedelta(minutes=5)).lease
        with self.assertRaises(ValueError):
            store.mark_started(lease.lease_id, " ")
        self.assertEqual(store.mark_started(lease.lease_id, "session-123").state, "started")
        store.release(lease.lease_id, "done for the day")
        self.assertEqual(store.active(), [])


class CliTestCase(_Base):
    def cli(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = cli.main(["--state-dir", str(self.state), *args])
        return code, out.getvalue()

    def files(self, issues=None, items=None, fetched_at=None):
        snapshot = write_json(self.tmp / "snapshot.json", {"fetched_at": (fetched_at or datetime.now(timezone.utc)).isoformat(), "issues": gate_issues() + (issues or [issue("PE0OM-700")]), "open_prs": []})
        queue = write_json(self.tmp / "queue.json", {"approved_by": "PO (test)", "approved_at": datetime.now(timezone.utc).isoformat(), "items": items or [self.item("PE0OM-700")]})
        return ["--snapshot", str(snapshot), "--queue", str(queue), "--repo", str(self.repo), "--worktree-root", str(self.worktrees)]

    def test_live_jira_is_not_configured(self):
        code, out = self.cli("--jira", "live", "preview", *self.files())
        self.assertEqual(code, cli.EXIT_NOT_CONFIGURED)
        self.assertIn(policy.NOT_CONFIGURED, out)

    def test_preview_and_claim_without_execute_write_nothing(self):
        for command in ("preview", "claim"):
            with self.subTest(command=command):
                code, out = self.cli(command, *self.files())
                self.assertEqual(code, cli.EXIT_OK, out)
        self.assertFalse(self.state.exists(), "dry-run created coordinator state")
        self.assertFalse(self.worktrees.exists(), "dry-run created a worktree")
        self.assertIn("would_claim", out)

    def test_execute_claims_creates_isolated_worktree_and_logs_evidence(self):
        args = self.files()
        code, out = self.cli("claim", "--execute", "--base", "HEAD", *args)
        self.assertEqual(code, cli.EXIT_OK, out)
        result = json.loads(out)
        claim = result["claims"]["PE0OM-700"]
        self.assertEqual(claim["status"], policy.CLAIMED)
        worktree = self.worktrees / "claude-PE0OM-700"
        self.assertTrue(worktree.is_dir())
        branch = subprocess.run(["git", "branch", "--show-current"], cwd=worktree, capture_output=True, text=True).stdout.strip()
        self.assertEqual(branch, "feature/PE0OM-700-task")
        log = [json.loads(line) for line in (self.state / "kickoff-log.jsonl").read_text().splitlines()]
        entry = next(e for e in log[-1]["entries"] if e["key"] == "PE0OM-700")
        for field in ("agent_role", "parent_epic", "blockers", "open_prs", "lease_id", "session_id", "status"):
            self.assertIn(field, entry)
        self.assertEqual(entry["status"], policy.CLAIMED)

        # Second run: the story is leased and the branch exists, so nothing is claimable.
        code, out = self.cli("claim", "--execute", "--base", "HEAD", *args)
        self.assertEqual(code, cli.EXIT_NO_RUN, out)

        code, out = self.cli("mark-started", "--lease-id", claim["lease_id"], "--session-id", "manual-session-1")
        self.assertEqual(code, cli.EXIT_OK)
        self.assertIn(policy.ACTUALLY_STARTED, out)

    def test_execute_refuses_on_no_run(self):
        code, _ = self.cli("claim", "--execute", "--base", "HEAD", *self.files(fetched_at=datetime.now(timezone.utc) - timedelta(hours=2)))
        self.assertEqual(code, cli.EXIT_NO_RUN)
        self.assertFalse(self.worktrees.exists())
        self.assertEqual(LeaseStore(self.state / "leases.db").active(), [])

    def test_manual_fallback_approve_records_digest_and_refuses_overwrite(self):
        snapshot = write_json(self.tmp / "snap.json", {"fetched_at": NOW.isoformat(), "issues": gate_issues() + [issue("PE0OM-710")], "open_prs": []})
        out_file = self.tmp / "approved.json"
        code, _ = self.cli("approve", "--snapshot", str(snapshot), "--item", "PE0OM-710:automation/x/", "--approved-by", "PO", "--out", str(out_file))
        self.assertEqual(code, cli.EXIT_OK)
        queue = load_queue(out_file)
        self.assertEqual(queue.items[0].acceptance_digest, acceptance_digest(AC))
        self.assertEqual(queue.items[0].agent, "claude")
        code, _ = self.cli("approve", "--snapshot", str(snapshot), "--item", "PE0OM-710:automation/x/", "--approved-by", "PO", "--out", str(out_file))
        self.assertEqual(code, cli.EXIT_ERROR)


if __name__ == "__main__":
    unittest.main()
