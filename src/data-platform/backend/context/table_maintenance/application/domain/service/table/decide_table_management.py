"""Define the decide_table_management domain service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table import TableManagementChange

if TYPE_CHECKING:
    from datetime import datetime

    from context.table_maintenance.application.domain.model.table import Table
    from context.table_maintenance.application.domain.model.table_discovery_policy import ManagementDecision


def decide_table_management(table: Table, decision: ManagementDecision, now: datetime) -> TableManagementChange:
    """Apply a management decision to a known table and say what changed.

    A decision to manage manages the table under what decided it; any other unmanages it under what
    decided it, or under nothing when no policy applies. A table whose management stays the same while
    what decided it moved (another policy, version or rule, managed or not) reports ``DECISION_CHANGED``,
    and so does an undecided table that becomes unmanaged, even with nothing deciding it: its status
    moved, so it is saved, and nothing is sent, since no maintenance workflow runs for it.
    A dropped table raises ``InvalidTableTransition``.
    """
    was_managed = table.is_managed
    previous = table.decided_by
    previous_status = table.status
    if decision.manage and decision.decided_by is not None:
        table.manage(decision.decided_by, now)
    else:
        table.unmanage(decision.decided_by, now)
    if was_managed == table.is_managed:
        unchanged = table.decided_by == previous and table.status == previous_status
        return TableManagementChange.UNCHANGED if unchanged else TableManagementChange.DECISION_CHANGED
    return TableManagementChange.MANAGED if table.is_managed else TableManagementChange.UNMANAGED
