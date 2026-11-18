"""External-write lockdown (PE0OM-75, PE0OM-56 slice 1/5).

Every connector client that can change an external business system calls
``guard_external_write`` immediately before the network request. Two independent
server-side boundaries apply, and both must pass before any live write could be sent:

1. Emergency kill switch: PARDHA_EXTERNAL_WRITES_ENABLED, off by default and read on
   every call. This is a lockdown control, NOT authorization.
2. Verified per-action authorization: an authenticated, exact-payload founder approval
   (centralized HITL, PE0OM-56 slice 4/5, PE0OM-78). That mechanism does not exist yet,
   so this boundary always denies. Enabling the kill switch alone can never cause a
   live external write in this slice.

There is deliberately no request parameter, client-supplied approval flag or identity
override that can satisfy boundary 2.
"""
from __future__ import annotations

import logging
import os

EXTERNAL_WRITES_ENV = "PARDHA_EXTERNAL_WRITES_ENABLED"
_TRUTHY = {"1", "true", "yes", "on"}

KILL_SWITCH = "kill_switch_disabled"
NO_VERIFIED_AUTHORIZATION = "no_verified_authorization"

logger = logging.getLogger(__name__)


class ExternalWriteBlocked(PermissionError):
    """Raised when an external write is attempted without passing every write boundary."""

    def __init__(self, connector: str, operation: str, reason: str):
        self.connector = connector
        self.operation = operation
        self.reason = reason
        if reason == KILL_SWITCH:
            detail = f"external writes are disabled ({EXTERNAL_WRITES_ENV} is not enabled)"
        else:
            detail = (
                "no verified exact-payload founder approval exists for this action; live external writes "
                "stay blocked until centralized HITL (PE0OM-78) is implemented"
            )
        super().__init__(f"External write blocked: {connector} {operation} was not sent because {detail}.")


def external_writes_enabled() -> bool:
    return os.getenv(EXTERNAL_WRITES_ENV, "").strip().lower() in _TRUTHY


def verified_write_authorization_available() -> bool:
    """Boundary 2. Always False until PE0OM-78 provides authenticated exact-payload approvals."""
    return False


def guard_external_write(connector: str, operation: str) -> None:
    """Raise ExternalWriteBlocked unless every external-write boundary passes (never, in this slice)."""
    if not external_writes_enabled():
        reason = KILL_SWITCH
    elif not verified_write_authorization_available():
        reason = NO_VERIFIED_AUTHORIZATION
    else:  # pragma: no cover - unreachable until PE0OM-78
        return
    logger.warning("Blocked external write: connector=%s operation=%s reason=%s", connector, operation, reason)
    raise ExternalWriteBlocked(connector, operation, reason)
