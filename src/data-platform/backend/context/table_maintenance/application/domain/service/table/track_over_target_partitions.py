"""Define the track_over_target_partitions domain service."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import OverTargetPartition

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime

    from context.table_maintenance.application.domain.model.shared import PartitionStats


def track_over_target_partitions(
    previous: Sequence[OverTargetPartition],
    over_target: Sequence[PartitionStats],
    now: datetime,
) -> tuple[OverTargetPartition, ...]:
    """Return the partitions now over the target with since when, sorted by spec id then values.

    A partition already tracked keeps its ``since``; a new one starts at ``now``; a tracked
    partition no longer over the target is dropped. The order does not follow ``over_target``, so
    two observations of the same partitions give equal results. A partition with a NaN or infinite
    value is left out: it cannot be stored as JSON and never compares equal to its stored copy.
    """
    tracked = {(entry.spec_id, entry.values): entry for entry in previous}
    entries = {
        (partition.spec_id, partition.values): tracked.get((partition.spec_id, partition.values))
        or OverTargetPartition(spec_id=partition.spec_id, values=partition.values, since=now)
        for partition in over_target
        if _is_finite(partition)
    }
    return tuple(sorted(entries.values(), key=lambda entry: (entry.spec_id, repr(entry.values))))


def _is_finite(partition: PartitionStats) -> bool:
    """Return whether no value of the partition is a NaN or infinite float."""
    return all(not isinstance(value, float) or math.isfinite(value) for value in partition.values)
