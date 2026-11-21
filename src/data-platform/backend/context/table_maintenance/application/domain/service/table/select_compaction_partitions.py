"""Define the select_compaction_partitions domain service."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import PartitionSelection

if TYPE_CHECKING:
    from collections.abc import Sequence

    from context.table_maintenance.application.domain.model.shared import OverTargetPartition, PartitionStats
    from context.table_maintenance.application.domain.model.table import PartitionSelectionSettings


def select_compaction_partitions(
    over_target: Sequence[tuple[PartitionStats, int]],
    tracked: Sequence[OverTargetPartition],
    now: datetime,
    settings: PartitionSelectionSettings,
) -> PartitionSelection:
    """Return the partitions a compaction job takes, and those that wait for writes to settle.

    Each pair of ``over_target`` is a partition over the target and its reducible files. The
    partitions are ordered by reducible files, most first, then by spec id and values. A partition
    waits while it was written within the quiet period and has been over the target for less than
    the longest wait; one whose last write is unknown does not wait. The job takes the first
    ``partitions_per_job`` partitions that do not wait.
    """
    since_by_partition = {(entry.spec_id, entry.values): entry.since for entry in tracked}
    ordered = sorted(over_target, key=lambda pair: (-pair[1], pair[0].spec_id, repr(pair[0].values)))
    allowed: list[PartitionStats] = []
    waiting: list[PartitionStats] = []
    waiting_until: datetime | None = None
    for partition, _reducible in ordered:
        since = since_by_partition.get((partition.spec_id, partition.values), now)
        ends = _wait_end(partition.last_written_at, since, now, settings)
        if ends is None:
            allowed.append(partition)
        else:
            waiting.append(partition)
            waiting_until = ends if waiting_until is None else min(waiting_until, ends)
    return PartitionSelection(
        selected=tuple(allowed[: settings.partitions_per_job]),
        waiting=tuple(waiting),
        waiting_until=waiting_until,
    )


def _wait_end(
    last_written_at: datetime | None,
    since: datetime,
    now: datetime,
    settings: PartitionSelectionSettings,
) -> datetime | None:
    """Return when a partition stops waiting, or None when it does not wait now."""
    if last_written_at is None or settings.quiet_period == timedelta(0):
        return None
    ends = min(last_written_at + settings.quiet_period, since + settings.max_quiet_wait)
    return ends if now < ends else None
