"""Test the OperationCooldowns value object."""

from __future__ import annotations

from datetime import timedelta

import pytest

from base import InvariantViolation
from context.table_maintenance.application.domain.model.shared import MaintenanceOperation
from context.table_maintenance.application.domain.model.table import OperationCooldowns


def test_platform_default_cooldowns():
    """The platform default is 1 hour, 6 hours, 6 hours and 7 days, with a 24 hour failure back-off cap."""
    c = OperationCooldowns.platform_default()
    assert [c.for_operation(op) for op in MaintenanceOperation.ordered()] == [
        timedelta(hours=1),
        timedelta(hours=6),
        timedelta(hours=6),
        timedelta(days=7),
    ]
    assert c.failure_backoff_cap == timedelta(hours=24)


def test_for_operation_reads_each_operations_own_cooldown():
    """Every operation reads its own field."""
    c = OperationCooldowns(
        rewrite_data_files=timedelta(minutes=1),
        rewrite_manifests=timedelta(minutes=2),
        expire_snapshots=timedelta(minutes=3),
        remove_orphan_files=timedelta(minutes=4),
        failure_backoff_cap=timedelta(hours=1),
    )
    assert [c.for_operation(op) for op in MaintenanceOperation.ordered()] == [
        timedelta(minutes=1),
        timedelta(minutes=2),
        timedelta(minutes=3),
        timedelta(minutes=4),
    ]


def test_a_cooldown_of_zero_is_allowed_but_the_orphan_interval_and_the_cap_must_be_positive():
    """Compaction, manifests and snapshots may have no cooldown; the interval and the cap may not be zero."""
    zero = timedelta(0)
    default = OperationCooldowns.platform_default()
    freed = default.with_changes(rewrite_data_files=zero)
    assert freed.for_operation(MaintenanceOperation.REWRITE_DATA_FILES) == zero
    with pytest.raises(InvariantViolation):
        default.with_changes(remove_orphan_files=zero)
    with pytest.raises(InvariantViolation):
        default.with_changes(failure_backoff_cap=zero)
    with pytest.raises(InvariantViolation):
        default.with_changes(rewrite_manifests=timedelta(seconds=-1))
