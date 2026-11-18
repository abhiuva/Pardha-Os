"""Test-database safety guard (PE0OM-75).

Automated tests must only ever touch a database that is provably disposable. When the
process is a test run, the configured DATABASE_URL is checked *before* any engine is
created, and the whole run stops immediately unless the database is one of:

* an in-memory SQLite database, or
* a SQLite file, given by an **absolute** path inside a temporary directory, that does
  **not exist yet** when the run starts, i.e. created fresh for this run (for example
  under ``mktemp -d``). Relative paths are refused because their meaning depends on the
  working directory.

A database *name* is never treated as proof of safety: "pardha_test" or
"test_feature.db" can still be a shared, persistent database. Server databases
(PostgreSQL and others) are refused, because the test runner can't prove that a server
database is disposable, and the developer database ``pardha_core`` lives on such a
server. If disposability can't be proven, the run fails closed.

Outside test runs this module does nothing; normal application startup is unchanged.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

_TRUTHY = {"1", "true", "yes", "on"}
_HINT = (
    "Use a fresh disposable SQLite database for every run, e.g. "
    'TEST_DB_DIR="$(mktemp -d)"; DATABASE_URL="sqlite:///$TEST_DB_DIR/pardha_test.db" '
    "(see docs/DEVELOPER_SETUP.md)."
)


class UnsafeTestDatabaseError(RuntimeError):
    """Raised when a test run is configured with a database not proven to be disposable."""


def running_under_tests() -> bool:
    if os.getenv("PARDHA_TESTING", "").strip().lower() in _TRUTHY:
        return True
    argv0 = sys.argv[0] if sys.argv else ""
    if "unittest" in argv0 or "pytest" in sys.modules:
        return True
    return Path(argv0).name.startswith("test_")


def _temp_roots() -> list[Path]:
    roots = {Path(tempfile.gettempdir()), Path("/tmp")}
    if os.getenv("TMPDIR"):
        roots.add(Path(os.environ["TMPDIR"]))
    resolved = set()
    for root in roots:
        try:
            resolved.add(root.resolve())
        except OSError:
            continue
    return sorted(resolved)


def _is_in_memory(database: str | None) -> bool:
    return not database or database == ":memory:" or database.startswith("file::memory:")


def assert_safe_test_database(database_url: str | None) -> None:
    """Raise UnsafeTestDatabaseError unless database_url is provably disposable for this run."""
    if not database_url:
        raise UnsafeTestDatabaseError(
            "Refusing to run tests: DATABASE_URL is not set, so the application would use the developer "
            f"PostgreSQL database. {_HINT}"
        )
    try:
        url = make_url(database_url)
    except ArgumentError as exc:
        raise UnsafeTestDatabaseError(f"Refusing to run tests: DATABASE_URL is not a valid database URL. {_HINT}") from exc

    backend = url.get_backend_name()
    if backend != "sqlite":
        raise UnsafeTestDatabaseError(
            f"Refusing to run tests against a '{backend}' server database: the test runner cannot prove it is "
            f"disposable, and the developer database lives on such a server. {_HINT}"
        )
    if _is_in_memory(url.database):
        return
    if not Path(url.database).expanduser().is_absolute():
        # A relative path's meaning depends on the working directory (e.g. a checkout that
        # happens to live under /tmp), so it can never prove disposability.
        raise UnsafeTestDatabaseError(
            f"Refusing to run tests against a relative SQLite path; use an absolute path in a fresh temporary directory. {_HINT}"
        )
    path = Path(url.database).expanduser().resolve()
    if not any(path.is_relative_to(root) for root in _temp_roots()):
        raise UnsafeTestDatabaseError(
            "Refusing to run tests against a SQLite file outside a temporary directory; a persistent file may "
            f"hold real data whatever its name. {_HINT}"
        )
    if path.exists():
        raise UnsafeTestDatabaseError(
            "Refusing to run tests against a SQLite file that already exists; every run needs a fresh "
            f"database that it creates itself. {_HINT}"
        )


def enforce_test_database_policy(database_url: str | None) -> None:
    """Stop a misconfigured test run immediately.

    Test loaders (unittest, pytest) catch exceptions raised while importing a test module
    and carry on with the remaining modules, so raising here would not stop the run. A
    misconfigured run terminates the whole process instead, before any engine exists.
    """
    if not running_under_tests():
        return
    try:
        assert_safe_test_database(database_url)
    except UnsafeTestDatabaseError as exc:
        sys.stderr.write(f"\n[pardha] {exc}\n")
        sys.stderr.flush()
        os._exit(2)
