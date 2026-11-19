"""Tests for the observe_compaction_partitions domain service."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from context.table_maintenance.application.domain.model.compaction_candidate import PartitionKey
from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation,
    OperationVerdict,
    PartitionFieldInfo,
    PartitionSpecInfo,
    PartitionStats,
    TableObservation,
)
from context.table_maintenance.application.domain.model.table import Table, TableId, TableName
from context.table_maintenance.application.domain.model.table_discovery_rules import TableDiscoveryRuleId
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    AtLeast,
    CompactionScope,
    CompactionUnit,
    MaintenancePolicyContent,
    RewriteDataFilesConditions,
)
from context.table_maintenance.application.domain.service.compaction_candidate import observe_compaction_partitions
from context.table_maintenance.application.domain.service.table import assess_maintenance

NOW = datetime(2026, 11, 13, 12, tzinfo=UTC)
DEFAULT = MaintenancePolicyContent.platform_default()
REGION = PartitionSpecInfo(
    spec_id=0,
    fields=(
        PartitionFieldInfo(
            field_id=1000, name="region", source_column="region", source_type="string", transform="identity"
        ),
    ),
)
UNPARTITIONED = PartitionSpecInfo(spec_id=0, fields=())


def _stats(values: tuple, files: int, *, spec_id: int = 0, size: int = 1000, written: datetime | None = None):  # noqa: ANN202
    return PartitionStats(
        spec_id=spec_id,
        values=values,
        data_file_count=files,
        position_delete_file_count=0,
        equality_delete_file_count=0,
        total_data_file_size_bytes=size,
        last_written_at=written,
    )


def _observation(partitions, specs=(REGION,)) -> TableObservation:  # noqa: ANN001
    return TableObservation(
        table_uuid="t-1",
        properties={},
        current_snapshot_id=1,
        specs=tuple(specs),
        partitions=tuple(partitions),
        manifests=(),
        snapshots=(),
    )


def _compaction(*, unit: CompactionUnit = CompactionUnit.PARTITION, at_least: int | None = 5, enabled: bool = True):
    rdf = DEFAULT.operations.rewrite_data_files
    trigger = rdf.trigger_policy.with_changes(
        conditions=RewriteDataFilesConditions(reducible_files=None if at_least is None else AtLeast(at_least=at_least)),
    )
    operations = DEFAULT.operations.with_changes(
        rewrite_data_files=rdf.with_changes(enabled=enabled, scope=CompactionScope(unit=unit), trigger_policy=trigger),
    )
    return DEFAULT.with_changes(operations=operations)


def test_each_partition_meeting_the_condition_is_observed():
    """Partitions with at least the policy's reducible files are observed, with their size, last write and label."""
    written = datetime(2026, 11, 13, 11, tzinfo=UTC)
    observed = observe_compaction_partitions(
        _compaction(), _observation([_stats(("eu",), 10, written=written), _stats(("us",), 3)])
    )
    (eu,) = observed
    assert eu.partition == PartitionKey(spec_id=0, values=("eu",))
    assert eu.label == "region=eu"
    assert eu.reducible_files == 9
    assert eu.data_bytes == 1000
    assert eu.last_written_at == written


def test_disabled_compaction_observes_nothing():
    """A policy that does not compact makes no partition a candidate."""
    assert observe_compaction_partitions(_compaction(enabled=False), _observation([_stats(("eu",), 10)])) == ()


def test_unpartitioned_table_has_one_whole_table_candidate():
    """An unpartitioned table's only partition stands for the whole table."""
    (whole,) = observe_compaction_partitions(_compaction(), _observation([_stats((), 10)], specs=(UNPARTITIONED,)))
    assert whole.partition == PartitionKey.whole_table()
    assert whole.label == "whole table"
    assert whole.reducible_files == 9


@pytest.mark.parametrize("at_least", [5, None])
def test_whole_table_policy_has_one_whole_table_candidate(at_least):
    """A whole-table policy (or one without a condition) has one candidate summing the whole table."""
    written = datetime(2026, 11, 13, 11, tzinfo=UTC)
    (whole,) = observe_compaction_partitions(
        _compaction(unit=CompactionUnit.TABLE if at_least else CompactionUnit.PARTITION, at_least=at_least),
        _observation([_stats(("eu",), 10, size=100), _stats(("us",), 3, size=50, written=written)]),
    )
    assert whole.partition == PartitionKey.whole_table()
    assert (whole.reducible_files, whole.data_bytes, whole.last_written_at) == (11, 150, written)


def test_whole_table_below_its_condition_observes_nothing():
    """A whole-table policy whose condition does not hold makes no candidate."""
    assert (
        observe_compaction_partitions(
            _compaction(unit=CompactionUnit.TABLE, at_least=50), _observation([_stats(("eu",), 10)])
        )
        == ()
    )


def test_a_qualifying_partition_of_an_unpartitioned_spec_makes_the_whole_table_the_candidate():
    """After partition evolution, an old unpartitioned spec cannot be filtered: the whole table is compacted."""
    spec1 = REGION.with_changes(spec_id=1)
    (whole,) = observe_compaction_partitions(
        _compaction(),
        _observation([_stats((), 10, spec_id=0), _stats(("eu",), 10, spec_id=1)], specs=(UNPARTITIONED, spec1)),
    )
    assert whole.partition.is_whole_table
    assert whole.reducible_files == 18


@pytest.mark.parametrize(
    ("policy", "partitions"),
    [
        (_compaction(), [_stats(("eu",), 10), _stats(("us",), 3)]),
        (_compaction(), [_stats(("eu",), 3)]),
        (_compaction(unit=CompactionUnit.TABLE, at_least=10), [_stats(("eu",), 6), _stats(("us",), 6)]),
        (_compaction(unit=CompactionUnit.TABLE, at_least=13), [_stats(("eu",), 6), _stats(("us",), 6)]),
        (_compaction(at_least=None), []),
        (_compaction(), []),
    ],
)
def test_candidates_exist_exactly_when_the_assessment_finds_compaction_due(policy, partitions):
    """Candidates sit under the policy: some partition is observed exactly when its conditions make compaction due."""
    table = Table.register(
        TableId("t-1"), TableName(catalog="c", namespace="n", table="t"), TableDiscoveryRuleId.new(), NOW
    )
    observation = _observation(partitions)
    (compaction,) = [
        a
        for a in assess_maintenance(table, policy, observation, NOW).operations
        if a.operation is MaintenanceOperation.REWRITE_DATA_FILES
    ]
    observed = observe_compaction_partitions(policy, observation)
    assert (compaction.verdict is OperationVerdict.DUE) == bool(observed)
