# Pardha two-agent story coordinator (PE0OM-82)

Decides which **human-approved** Jira stories Claude Code and Codex may start, claims them atomically,
and gives each one its own Git worktree and branch. **Dry-run is the default.** It never merges,
deploys, pushes, writes to Jira or any live connector, launches a model, or touches a protected branch.

Standard library only (Python 3.9+). Run from the repository root:

```bash
python -m automation.coordinator preview --snapshot snapshot.json --queue queue.json \
    --repo . --worktree-root ../pardha-worktrees
```

## Flow

1. **Snapshot (read-only).** A human, or a read-only tool, exports the Jira issues and open PRs to
   `snapshot.json` (format below). There is no live Jira client: `--jira live` returns
   `NOT CONFIGURED` until a secure, narrowly scoped coordinator integration is verified.
2. **Preview.** `preview` lists every approved and every `ai-ready` in-scope story with `READY`/`BLOCKED`
   and the reasons. It writes nothing (only `--log-file`, if given).
3. **Approve (manual fallback).** `approve --item KEY:path1,path2 --approved-by NAME --out queue.json`
   records pasted keys with their file-path reservations and the current acceptance-criteria digest.
   It refuses to overwrite an existing queue.
4. **Claim.** `claim` is a dry-run that reports `would_claim`. `claim --execute` takes an atomic lease
   for at most one story per agent, then creates a **new** branch in a **new** worktree from
   `origin/develop`. If worktree creation fails, the lease is released.
5. **Launch (manual).** The output prints the launch command. After a human starts the session,
   `mark-started --lease-id … --session-id …` records `ACTUALLY STARTED`.
6. **Release** with `release --lease-id … --reason …`. Leases expire after the agent's budget
   (Claude 180 min, Codex 120 min); expiries are logged.

## Selection rules

A story is `READY` only if **all** of these hold:
- in scope: label `pardha-v1-dec7` or `pardha-mvp`, or explicitly listed in the approved queue (allowlist);
- labelled `ai-ready` and exactly one of `ai-owner-claude` / `ai-owner-codex`, matching the queue's agent;
- not labelled `ai-blocked`, `ai-pr-review` or `v1-deferred`;
- status `To Do`, with acceptance criteria in the description;
- every "is blocked by" issue is `Done`;
- no open PR, and no existing branch or worktree, names the issue;
- the approved branch is new, not protected, uses the agent's prefix and names the issue;
- the file-path reservations are owned by that agent and overlap no active lease.

Only stories in the human-approved queue can be selected. Newly labelled stories appear in the
preview but are never auto-picked.

## No-run conditions (nothing is claimed)

- the snapshot is missing, malformed, older than 30 minutes, or dated in the future;
- any readiness-gate issue is missing from the snapshot (PE0OM-93, PE0OM-75…79, PE0OM-33);
- an approved story's acceptance criteria changed since approval (digest mismatch);
- an approved story has a dependency missing from the snapshot (ambiguous dependency);
- no approved queue was supplied;
- live Jira was requested (`NOT CONFIGURED`).

## Ownership (mutually exclusive)

The longest matching prefix decides which agent owns a path. A reservation that would contain the other
agent's territory, or a path no agent owns (e.g. `CLAUDE.md`), is refused.

| Agent | Owns |
|---|---|
| claude | `pardha-core/`, `automation/`, `docs/architecture/` |
| codex | `pardha-core/dashboard/`, `pardha-core/tests/test_adversarial_`, `pardha-core/tests/e2e/`, `docs/qa/` |

## Atomic claiming

Leases live in a local SQLite file (`--state-dir`, default `~/.pardha-coordinator`). A claim runs in one
`BEGIN IMMEDIATE` transaction: expire stale leases, check conflicts, insert, log. Partial unique indexes
enforce one active lease per issue, per agent and per worktree independently of the check. After the commit,
the claimer reads the lease back and only proceeds if the store still says it is theirs. Every claim,
refusal, expiry, start and release is recorded in `lease_events`.

## Kickoff log

`kickoff-log.jsonl` (state dir, or `--log-file`): one line per run with date and time (Asia/Kolkata), mode, run status,
no-run reasons, readiness-gate statuses, and for each story: key, agent role, parent epic, status
(`READY`, `BLOCKED`, `CLAIMED`, `ACTUALLY STARTED`), blockers, open PRs, lease id, session id, branch and worktree.

## File formats

`snapshot.json`:
```json
{"fetched_at": "2026-11-18T03:00:00+00:00", "source": "…",
 "issues": [{"key": "PE0OM-82", "summary": "…", "status": "To Do", "labels": ["ai-ready"],
             "description": "… Acceptance criteria …", "parent": "PE0OM-35", "blocked_by": ["PE0OM-75"]}],
 "open_prs": [{"number": 6, "head": "feature/PE0OM-75-…", "title": "…"}]}
```

`queue.json` (written by `approve`, or by hand):
```json
{"approved_by": "Product Owner", "approved_at": "2026-11-18T03:00:00+00:00",
 "items": [{"key": "PE0OM-82", "agent": "claude", "acceptance_digest": "sha256:…",
            "branch": "feature/PE0OM-82-…", "paths": ["automation/"]}]}
```

Exit codes: `0` ready/ok, `1` error, `2` no-run or nothing claimable, `3` not configured.

## Not implemented (deliberately)

- Live Jira reads, Jira status transitions and comments: need verified, narrowly scoped coordinator credentials and PO approval.
- Authenticated coordinator API: depends on API authentication (PE0OM-76).
- Automatic 08:30 scheduling (cron/launchd) and automatic agent launch: need PO approval. The preview reports whether the weekday 08:30 Asia/Kolkata window is open.

## Tests

`python -m unittest discover -s automation/tests -t .` runs isolated tests: temporary directories, a throwaway Git
repository, network connections blocked.
