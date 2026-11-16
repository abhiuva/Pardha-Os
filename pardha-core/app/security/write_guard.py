"""External-write lockdown (PE0OM-75, PE0OM-56 slice 1/5).

Every connector client that can change an external business system calls
``guard_external_write`` immediately before the network request. Writes are disabled
unless PARDHA_EXTERNAL_WRITES_ENABLED is explicitly set to a true value, so the default
is fail-closed. The setting is read on every call, never cached.

This switch is an outer safety boundary only. It does not replace the per-action founder
approval required in V1 (centralized HITL, PE0OM-56 slice 4/5).
"""
from __future__ import annotations

import logging
import os

EXTERNAL_WRITES_ENV = "PARDHA_EXTERNAL_WRITES_ENABLED"
_TRUTHY = {"1", "true", "yes", "on"}

logger = logging.getLogger(__name__)


class ExternalWriteBlocked(PermissionError):
    """Raised when an external write is attempted while external writes are disabled."""

    def __init__(self, connector: str, operation: str):
        self.connector = connector
        self.operation = operation
        super().__init__(
            f"External write blocked: {connector} {operation} was not sent because external writes are disabled "
            f"({EXTERNAL_WRITES_ENV} is not enabled)."
        )


def external_writes_enabled() -> bool:
    return os.getenv(EXTERNAL_WRITES_ENV, "").strip().lower() in _TRUTHY


def guard_external_write(connector: str, operation: str) -> None:
    """Raise ExternalWriteBlocked unless external writes are explicitly enabled."""
    if not external_writes_enabled():
        logger.warning("Blocked external write: connector=%s operation=%s", connector, operation)
        raise ExternalWriteBlocked(connector, operation)
