"""Git inspection (read-only) and the single local write the coordinator may make:
`git worktree add -b <new branch>` for an approved, freshly claimed task.

Never: checkout in an existing worktree, reset, clean, delete, push, or touch a protected branch.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from automation.coordinator.policy import PROTECTED_BRANCHES

Runner = Callable[[Sequence[str], Path], subprocess.CompletedProcess]


def _default_runner(args: Sequence[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(list(args), cwd=cwd, capture_output=True, text=True, check=False, timeout=60)


@dataclass(frozen=True)
class Worktree:
    path: str
    branch: str | None


class GitState:
    def __init__(self, repo: Path, runner: Runner = _default_runner):
        self.repo = Path(repo)
        self.run = runner

    def _git(self, *args: str) -> subprocess.CompletedProcess:
        return self.run(["git", *args], self.repo)

    def worktrees(self) -> list[Worktree]:
        result = self._git("worktree", "list", "--porcelain")
        if result.returncode != 0:
            raise RuntimeError(f"git worktree list failed: {result.stderr.strip()}")
        items: list[Worktree] = []
        path: str | None = None
        branch: str | None = None
        for line in result.stdout.splitlines() + [""]:
            if line.startswith("worktree "):
                path, branch = line[len("worktree "):], None
            elif line.startswith("branch "):
                branch = line[len("branch "):].removeprefix("refs/heads/")
            elif not line and path is not None:
                items.append(Worktree(path, branch))
                path = None
        return items

    def branch_exists(self, branch: str) -> bool:
        for ref in (f"refs/heads/{branch}", f"refs/remotes/origin/{branch}"):
            if self._git("rev-parse", "--verify", "--quiet", ref).returncode == 0:
                return True
        return False

    def branches(self) -> list[str]:
        """All local and remote-tracking branch names (remote prefix stripped)."""
        result = self._git("for-each-ref", "--format=%(refname)", "refs/heads", "refs/remotes")
        if result.returncode != 0:
            raise RuntimeError(f"git for-each-ref failed: {result.stderr.strip()}")
        names = set()
        for ref in result.stdout.split():
            if ref.startswith("refs/heads/"):
                names.add(ref[len("refs/heads/"):])
            elif ref.startswith("refs/remotes/") and not ref.endswith("/HEAD"):
                names.add(ref.split("/", 3)[3])
        return sorted(names)

    def is_dirty(self, path: str) -> bool:
        result = self.run(["git", "status", "--porcelain"], Path(path))
        return result.returncode != 0 or bool(result.stdout.strip())

    def create_worktree(self, path: str, branch: str, base: str) -> None:
        """Create a NEW branch in a NEW worktree. Refuses anything that could overwrite work."""
        if branch in PROTECTED_BRANCHES:
            raise RuntimeError(f"refusing to create protected branch {branch}")
        if self.branch_exists(branch):
            raise RuntimeError(f"branch {branch} already exists; never overwritten")
        if Path(path).exists():
            raise RuntimeError(f"worktree path {path} already exists")
        result = self._git("worktree", "add", "--no-track", "-b", branch, path, base)
        if result.returncode != 0:
            raise RuntimeError(f"git worktree add failed: {result.stderr.strip()}")
