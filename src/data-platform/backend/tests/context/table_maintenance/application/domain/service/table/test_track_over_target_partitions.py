"""Test the track_over_target_partitions domain service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from context.table_maintenance.application.domain.model.shared import OverTargetPartition, PartitionStats
from context.table_maintenance.application.domain.service.table import track_over_target_partitions

NOW = datetime(2026, 11, 20, 12, tzinfo=UTC)


def p(spec_id, *values, written=None, files=10):
    """Build the stats of one partition."""
    return PartitionStats(
        spec_id=spec_id,
        values=values,
        data_file_count=files,
        position_delete_file_count=0,
        equality_delete_file_count=0,
        total_data_file_size_bytes=0,
        last_written_at=written,
    )


def since(partition, at):
    """Build the over-target entry of a partition."""
    return OverTargetPartition(spec_id=partition.spec_id, values=partition.values, since=at)


def test_a_new_partition_over_target_is_tracked_since_now():
    """A partition seen over the target for the first time is tracked since now."""
    assert track_over_target_partitions((), [p(0, "eu")], NOW) == (
        OverTargetPartition(spec_id=0, values=("eu",), since=NOW),
    )


def test_a_tracked_partition_keeps_its_since():
    """A partition already tracked keeps the time it was first seen."""
    eu = p(0, "eu")
    assert track_over_target_partitions((since(eu, NOW - timedelta(hours=2)),), [eu], NOW) == (
        since(eu, NOW - timedelta(hours=2)),
    )


def test_a_partition_back_under_target_is_dropped():
    """A tracked partition no longer over the target is dropped."""
    assert track_over_target_partitions((since(p(0, "eu"), NOW),), [], NOW) == ()


def test_the_same_values_in_two_specs_are_two_entries():
    """The same values in two specs are two partitions, each with its own since."""
    old = since(p(0, "eu"), NOW - timedelta(hours=1))
    assert track_over_target_partitions((old,), [p(0, "eu"), p(1, "eu")], NOW) == (old, since(p(1, "eu"), NOW))


def test_the_result_does_not_depend_on_the_order_of_the_observation():
    """The same partitions in two orders give equal results, sorted by spec then values."""
    a, b, c = p(1, "a"), p(0, "b"), p(0, "a")
    forward = track_over_target_partitions((), [a, b, c], NOW)
    backward = track_over_target_partitions((), [c, b, a], NOW)
    assert forward == backward
    assert [(t.spec_id, t.values) for t in forward] == [(0, ("a",)), (0, ("b",)), (1, ("a",))]


def test_a_round_tripped_entry_still_matches():
    """An entry stored and loaded still matches the partition it was tracked from."""
    observed = p(0, 1, 1.5, True, None, "o'neil")
    entry = track_over_target_partitions((), [observed], NOW)[0]
    assert OverTargetPartition.from_primitives(entry.to_primitives()).is_of(observed)
