"""Define the OperationVerdict enumeration."""

from __future__ import annotations

from enum import StrEnum


class OperationVerdict(StrEnum):
    """Enumerate what the maintenance evaluation concludes for one operation."""

    DUE = "due"
    NOT_DUE = "not_due"
    DISABLED = "disabled"
    COOLDOWN = "cooldown"
