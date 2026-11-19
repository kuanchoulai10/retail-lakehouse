"""Define the TableReconciliationId identifier."""

from __future__ import annotations

from typing import ClassVar

from base import EntityId


class TableReconciliationId(EntityId):
    """Identify a TableReconciliation; the reconciliation workflow mints it as an ``rc-`` id."""

    PREFIX: ClassVar[str | None] = "rc"
