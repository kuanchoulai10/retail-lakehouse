"""Define the TableReconciliationId identifier."""

from __future__ import annotations

from typing import ClassVar

from base import EntityId


class TableReconciliationId(EntityId):
    """Identify a TableReconciliation; an ``rc-`` id the application issues (ADR 0015)."""

    PREFIX: ClassVar[str | None] = "rc"
