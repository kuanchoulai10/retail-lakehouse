"""Define the SendTableChangeGatewayInput."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SendTableChangeGatewayInput:
    """Name the table, what changed about it and whether it is enrolled.

    ``table_name`` is the fully qualified ``catalog.namespace.table`` name.
    ``change`` is a ``TableChange`` value. ``operations`` is used only by
    ``maintenance_requested``.
    """

    table_uuid: str
    table_name: str
    change: str
    is_enrolled: bool
    operations: list[str] = field(default_factory=list)
