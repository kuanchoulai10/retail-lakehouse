"""Define the OperationVerdict enumeration."""

from __future__ import annotations

from enum import StrEnum


class OperationVerdict(StrEnum):
    """Enumerate what the maintenance evaluation concludes for one operation."""

    DUE = "due"
    WAITING_FOR_WRITES = "waiting_for_writes"
    NOT_DUE = "not_due"
    DISABLED = "disabled"
    COOLDOWN = "cooldown"
    NEEDS_ATTENTION = "needs_attention"
