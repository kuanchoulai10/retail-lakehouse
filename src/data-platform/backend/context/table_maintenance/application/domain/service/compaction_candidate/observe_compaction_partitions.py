"""Define the observe_compaction_partitions domain service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.compaction_candidate import (
    ObservedPartition,
    PartitionKey,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy import CompactionUnit
from context.table_maintenance.application.domain.service.compaction_candidate.partition_label import (
    WHOLE_TABLE_LABEL,
    partition_label,
)
from context.table_maintenance.application.domain.service.shared import resolve_target_file_size
from context.table_maintenance.application.domain.service.table import compute_reducible_files

if TYPE_CHECKING:
    from collections.abc import Sequence

    from context.table_maintenance.application.domain.model.shared import PartitionStats, TableObservation
    from context.table_maintenance.application.domain.model.table_maintenance_policy import MaintenancePolicyContent


def observe_compaction_partitions(
    policy: MaintenancePolicyContent, observation: TableObservation
) -> tuple[ObservedPartition, ...]:
    """Return the partitions that meet the policy's compaction conditions in ``observation``.

    Candidates sit under the policy, so this follows the assessment's rule: a
    partition-scoped policy with a ``reducible_files`` condition yields each
    partition with at least that many removable files, unless one of them lies
    in an unpartitioned spec (it cannot be filtered); a whole-table policy, a
    policy without a condition, an unpartitioned table and that case yield one
    whole-table partition summing the whole table, when the condition holds for
    the table. A disabled compaction yields nothing.
    """
    compaction = policy.operations.rewrite_data_files
    if not compaction.enabled:
        return ()
    condition = compaction.trigger_policy.conditions.reducible_files
    target = resolve_target_file_size(observation.properties)
    reducible = [(p, compute_reducible_files(p, target)) for p in observation.partitions]
    if compaction.scope.unit == CompactionUnit.TABLE or condition is None:
        whole = _whole_table(reducible)
        if condition is not None and whole.reducible_files < condition.at_least:
            return ()
        return (whole,)
    qualifying = [(p, r) for p, r in reducible if r >= condition.at_least]
    if not qualifying:
        return ()
    partitioned = {s.spec_id for s in observation.specs if not s.is_unpartitioned}
    if any(p.spec_id not in partitioned for p, _ in qualifying):
        return (_whole_table(reducible),)
    return tuple(_partition(observation, p, r) for p, r in qualifying)


def _partition(observation: TableObservation, stats: PartitionStats, reducible: int) -> ObservedPartition:
    key = PartitionKey(spec_id=stats.spec_id, values=stats.values)
    return ObservedPartition(
        partition=key,
        label=partition_label(observation.specs, key),
        reducible_files=reducible,
        data_bytes=stats.total_data_file_size_bytes,
        last_written_at=stats.last_written_at,
    )


def _whole_table(reducible: Sequence[tuple[PartitionStats, int]]) -> ObservedPartition:
    written = [p.last_written_at for p, _ in reducible if p.last_written_at is not None]
    return ObservedPartition(
        partition=PartitionKey.whole_table(),
        label=WHOLE_TABLE_LABEL,
        reducible_files=sum(r for _, r in reducible),
        data_bytes=sum(p.total_data_file_size_bytes for p, _ in reducible),
        last_written_at=max(written) if written else None,
    )
