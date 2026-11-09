"""Define the ReconciliationOutcome enumeration."""

from __future__ import annotations

from enum import StrEnum


class ReconciliationOutcome(StrEnum):
    """Enumerate whether a reconciliation assessed the table or skipped it."""

    PLANNED = "planned"
    SKIPPED = "skipped"
