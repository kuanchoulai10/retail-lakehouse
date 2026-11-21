"""Define the decide_table_management domain service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table import TableManagementChange

if TYPE_CHECKING:
    from datetime import datetime

    from context.table_maintenance.application.domain.model.table import Table
    from context.table_maintenance.application.domain.model.table_discovery_policy import DiscoveryDecision


def decide_table_management(table: Table, decision: DiscoveryDecision, now: datetime) -> TableManagementChange:
    """Apply a discovery decision to a known table and say what changed.

    A managing decision manages the table under its match, an unmanaging one unmanages it under
    its match. A table whose management stays the same while the match moved (another policy,
    version or rule, managed or not) reports ``MATCH_CHANGED``. A dropped table raises
    ``InvalidTableTransition``.
    """
    was_managed = table.is_managed
    previous = table.discovered_by
    if decision.manages:
        table.manage(decision.match, now)
    else:
        table.unmanage(decision.match, now)
    if was_managed == table.is_managed:
        return (
            TableManagementChange.UNCHANGED if table.discovered_by == previous else TableManagementChange.MATCH_CHANGED
        )
    return TableManagementChange.MANAGED if table.is_managed else TableManagementChange.UNMANAGED
