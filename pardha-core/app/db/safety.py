"""Test-database safety guard (PE0OM-75).

Automated tests must only ever touch a disposable database. When the process is a test
run, the configured DATABASE_URL is checked *before* any engine is created, and the run
fails immediately if it could point at the normal developer or a production database.
Outside test runs this module does nothing.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

DEVELOPER_DATABASE_NAMES = frozenset({"pardha_core"})
_TRUTHY = {"1", "true", "yes", "on"}


class UnsafeTestDatabaseError(RuntimeError):
    """Raised when a test run is configured with a non-disposable database."""


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


def _is_disposable_sqlite(database: str | None) -> bool:
    if not database or database == ":memory:" or database.startswith("file::memory:"):
        return True
    path = Path(database).expanduser().resolve()
    if "test" in path.name.lower():
        return True
    return any(path.is_relative_to(root) for root in _temp_roots())


def _is_disposable_server_database(database: str | None) -> bool:
    if not database or database.lower() in DEVELOPER_DATABASE_NAMES:
        return False
    name = database.lower()
    return name.endswith("_test") or name.startswith("test_")


def assert_safe_test_database(database_url: str | None) -> None:
    """Raise UnsafeTestDatabaseError unless database_url is clearly disposable."""
    hint = (
        "Set DATABASE_URL to a disposable test database, e.g. "
        "sqlite:///$(mktemp -d)/pardha_test.db, or a server database whose name ends in _test."
    )
    if not database_url:
        raise UnsafeTestDatabaseError(
            "Refusing to run tests: DATABASE_URL is not set, so the application would use the "
            f"developer PostgreSQL database. {hint}"
        )
    try:
        url = make_url(database_url)
    except ArgumentError as exc:
        raise UnsafeTestDatabaseError(f"Refusing to run tests: DATABASE_URL is not a valid database URL. {hint}") from exc

    backend = url.get_backend_name()
    if backend == "sqlite":
        if _is_disposable_sqlite(url.database):
            return
        raise UnsafeTestDatabaseError(
            "Refusing to run tests against a SQLite file that is neither in a temporary directory "
            f"nor named as a test database. {hint}"
        )
    if backend == "postgresql":
        if _is_disposable_server_database(url.database):
            return
        raise UnsafeTestDatabaseError(
            "Refusing to run tests against a PostgreSQL database that is not a dedicated test "
            f"database. {hint}"
        )
    raise UnsafeTestDatabaseError(f"Refusing to run tests against unsupported database backend '{backend}'. {hint}")


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
