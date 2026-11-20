"""Test the resolution of a table's snapshot retention."""

from __future__ import annotations

from datetime import timedelta

import pytest

from base import InvariantViolation
from context.table_maintenance.application.domain.model.shared import SnapshotRetention
from context.table_maintenance.application.domain.model.table_maintenance_policy import ExpireSnapshotsTarget
from context.table_maintenance.application.domain.service.shared import resolve_snapshot_retention

MIN_KEY = "history.expire.min-snapshots-to-keep"
AGE_KEY = "history.expire.max-snapshot-age-ms"


def test_retention_policy_wins():
    """Where the target and the table properties overlap, the target wins."""
    target = ExpireSnapshotsTarget(min_snapshots_to_keep=10, max_snapshot_age=timedelta(days=1))
    properties = {MIN_KEY: "3", AGE_KEY: str(2 * 86400 * 1000)}
    assert resolve_snapshot_retention(target, properties) == SnapshotRetention(
        min_snapshots_to_keep=10, max_snapshot_age=timedelta(days=1)
    )


def test_retention_falls_back_to_the_table():
    """A value the target leaves out is the table property's."""
    target = ExpireSnapshotsTarget(max_snapshot_age=timedelta(days=1))
    assert resolve_snapshot_retention(target, {MIN_KEY: "3"}) == SnapshotRetention(
        min_snapshots_to_keep=3, max_snapshot_age=timedelta(days=1)
    )


def test_retention_reads_milliseconds():
    """The age property is in milliseconds."""
    retention = resolve_snapshot_retention(ExpireSnapshotsTarget(), {AGE_KEY: "172800000"})
    assert retention.max_snapshot_age == timedelta(days=2)


def test_retention_floors_milliseconds_to_whole_seconds():
    """An age that is not whole seconds is floored to them."""
    retention = resolve_snapshot_retention(ExpireSnapshotsTarget(), {AGE_KEY: "1999"})
    assert retention.max_snapshot_age == timedelta(seconds=1)


@pytest.mark.parametrize("raw", ["abc", "0", "-5", "999"])
def test_retention_ignores_a_malformed_property(raw: str):
    """An age that is not a positive number of milliseconds of at least a second falls back to five days."""
    retention = resolve_snapshot_retention(None, {AGE_KEY: raw})
    assert retention.max_snapshot_age == timedelta(days=5)


@pytest.mark.parametrize("raw", ["abc", "0", "-5"])
def test_retention_ignores_a_malformed_count(raw: str):
    """A count that is not a positive whole number falls back to one snapshot."""
    assert resolve_snapshot_retention(None, {MIN_KEY: raw}).min_snapshots_to_keep == 1


def test_retention_without_a_block_is_icebergs_default():
    """Without a target and without properties, Iceberg keeps one snapshot and five days."""
    assert resolve_snapshot_retention(None, {}) == SnapshotRetention(
        min_snapshots_to_keep=1, max_snapshot_age=timedelta(days=5)
    )


def test_a_retention_keeps_at_least_one_snapshot():
    """A retention keeping no snapshot is refused."""
    with pytest.raises(InvariantViolation):
        SnapshotRetention(min_snapshots_to_keep=0, max_snapshot_age=timedelta(days=1))
