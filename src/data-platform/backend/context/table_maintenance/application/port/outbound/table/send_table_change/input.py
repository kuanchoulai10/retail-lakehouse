"""Define the SendTableChangeGatewayInput."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SendTableChangeGatewayInput:
    """Name the table, what changed about it and whether it is managed.

    ``table_name`` is the fully qualified ``catalog.namespace.table`` name.
    ``change`` is a ``TableChange`` value. ``operations`` and ``priority`` (a
    ``TablePriority`` value, or ``None`` for the table's own) are used only by
    ``maintenance_requested``.
    """

    table_uuid: str
    table_name: str
    change: str
    is_managed: bool
    operations: list[str] = field(default_factory=list)
    priority: str | None = None
