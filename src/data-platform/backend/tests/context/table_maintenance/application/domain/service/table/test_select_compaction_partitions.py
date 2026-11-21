"""Test the select_compaction_partitions domain service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from context.table_maintenance.application.domain.model.shared import (
    OverTargetPartition,
    PartitionSelection,
    PartitionStats,
)
from context.table_maintenance.application.domain.model.table import PartitionSelectionSettings
from context.table_maintenance.application.domain.service.table import select_compaction_partitions

NOW = datetime(2026, 11, 20, 12, tzinfo=UTC)
SETTINGS = PartitionSelectionSettings.platform_default()


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


def test_nothing_over_target_selects_nothing():
    """With no partition over the target nothing is selected or waiting."""
    assert select_compaction_partitions([], [], NOW, SETTINGS) == PartitionSelection()


def test_quiet_partitions_are_all_selected_under_the_cap():
    """Quiet partitions below the cap are all selected."""
    over = [(p(0, r), 5) for r in ("a", "b", "c")]
    got = select_compaction_partitions(over, [], NOW, SETTINGS)
    assert (len(got.selected), got.waiting, got.waiting_until) == (3, (), None)


def test_the_cap_takes_the_most_reducible_first():
    """Over the cap, the partitions with the most reducible files are taken."""
    over = [(p(0, f"r{i:02}"), i) for i in range(1, 13)]
    got = select_compaction_partitions(over, [], NOW, SETTINGS)
    assert [s.values[0] for s in got.selected] == [f"r{i:02}" for i in range(12, 2, -1)]


def test_ties_break_by_spec_then_values():
    """Equal reducible files break by spec id, then by values."""
    over = [(p(0, "b"), 5), (p(1, "a"), 5), (p(0, "a"), 5)]
    got = select_compaction_partitions(over, [], NOW, SETTINGS)
    assert [(s.spec_id, s.values) for s in got.selected] == [(0, ("a",)), (0, ("b",)), (1, ("a",))]


def test_a_recently_written_partition_waits():
    """A partition written within the quiet period waits until the period ends."""
    hot = p(0, "hot", written=NOW - timedelta(seconds=30))
    got = select_compaction_partitions([(hot, 5), (p(0, "cold"), 5)], [], NOW, SETTINGS)
    assert ([s.values for s in got.selected], [w.values for w in got.waiting]) == ([("cold",)], [("hot",)])
    assert got.waiting_until == NOW + timedelta(seconds=90)


def test_every_partition_waiting_is_all_waiting():
    """When every partition waits, nothing is selected and all_waiting holds."""
    hot = p(0, "hot", written=NOW - timedelta(seconds=30))
    got = select_compaction_partitions([(hot, 5)], [], NOW, SETTINGS)
    assert (got.all_waiting, got.selected) == (True, ())


def test_a_partition_over_target_past_the_max_wait_runs_while_written():
    """A partition over the target for the longest wait runs even while written."""
    hot = p(0, "hot", written=NOW - timedelta(seconds=10))
    got = select_compaction_partitions([(hot, 5)], [since(hot, NOW - timedelta(minutes=61))], NOW, SETTINGS)
    assert (got.selected, got.waiting) == ((hot,), ())


def test_waiting_until_is_the_max_wait_when_it_comes_first():
    """The wait ends at the longest wait when that comes before the quiet period ends."""
    hot = p(0, "hot", written=NOW - timedelta(seconds=10))
    got = select_compaction_partitions([(hot, 5)], [since(hot, NOW - timedelta(minutes=59))], NOW, SETTINGS)
    assert got.waiting_until == NOW + timedelta(minutes=1)


def test_waiting_until_is_the_earliest_over_the_waiting_partitions():
    """With several waiting partitions the earliest end is reported."""
    late = p(0, "late", written=NOW - timedelta(seconds=10))
    early = p(0, "early", written=NOW - timedelta(seconds=100))
    got = select_compaction_partitions([(late, 5), (early, 5)], [], NOW, SETTINGS)
    assert (len(got.waiting), got.waiting_until) == (2, NOW + timedelta(seconds=20))


def test_an_unknown_last_write_counts_as_quiet():
    """A partition whose last write is unknown does not wait."""
    got = select_compaction_partitions([(p(0, "eu", written=None), 5)], [], NOW, SETTINGS)
    assert (len(got.selected), got.waiting) == (1, ())


def test_a_future_last_write_waits_out_the_quiet_period_after_it():
    """A write dated in the future waits until the quiet period after it, and is bounded by the longest wait."""
    skewed = p(0, "eu", written=NOW + timedelta(minutes=5))
    fresh = select_compaction_partitions([(skewed, 5)], [], NOW, SETTINGS)
    assert (fresh.all_waiting, fresh.waiting_until) == (True, NOW + timedelta(minutes=7))
    old = select_compaction_partitions([(skewed, 5)], [since(skewed, NOW - timedelta(hours=1))], NOW, SETTINGS)
    assert old.selected == (skewed,)


def test_zero_quiet_period_never_waits():
    """A quiet period of zero lets every partition run."""
    hot = p(0, "hot", written=NOW)
    got = select_compaction_partitions([(hot, 5)], [], NOW, SETTINGS.with_changes(quiet_period=timedelta(0)))
    assert got.selected == (hot,)


def test_zero_max_wait_never_waits():
    """A longest wait of zero lets every partition run."""
    hot = p(0, "hot", written=NOW)
    got = select_compaction_partitions([(hot, 5)], [], NOW, SETTINGS.with_changes(max_quiet_wait=timedelta(0)))
    assert got.selected == (hot,)


def test_waiting_partitions_do_not_count_toward_the_cap():
    """Waiting partitions take no place under the cap."""
    hot = [(p(0, f"h{i}", written=NOW), 50) for i in range(2)]
    quiet = [(p(0, f"q{i}"), 5) for i in range(3)]
    got = select_compaction_partitions(hot + quiet, [], NOW, SETTINGS.with_changes(partitions_per_job=2))
    assert ([s.values for s in got.selected], len(got.waiting)) == ([("q0",), ("q1",)], 2)


def test_partitions_of_two_specs_are_selected_together():
    """Partitions of two specs with equal values are two selections, most reducible first."""
    got = select_compaction_partitions([(p(0, "eu"), 5), (p(1, "eu"), 7)], [], NOW, SETTINGS)
    assert [s.spec_id for s in got.selected] == [1, 0]


def test_waiting_is_in_the_selection_order():
    """The waiting partitions are listed most reducible first, like the selected ones."""
    over = [(p(0, "a", written=NOW), 3), (p(0, "b", written=NOW), 9)]
    got = select_compaction_partitions(over, [], NOW, SETTINGS)
    assert [w.values for w in got.waiting] == [("b",), ("a",)]
