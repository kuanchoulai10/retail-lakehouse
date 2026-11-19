"""Tests for the estimate_throughput domain service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from context.table_maintenance.application.domain.model.shared import MaintenanceOperation
from context.table_maintenance.application.domain.model.table import TableId
from context.table_maintenance.application.domain.model.table_maintenance_run import (
    TableMaintenanceRun,
    TableMaintenanceRunId,
    TriggerType,
)
from context.table_maintenance.application.domain.service.compaction_candidate import estimate_throughput

NOW = datetime(2026, 11, 13, 12, tzinfo=UTC)
GIB = 1024**3
DEFAULT = 2.0 * GIB
COMPACTION = MaintenanceOperation.REWRITE_DATA_FILES


def _run(
    *,
    rewritten: int | None = GIB,
    minutes: float = 30,
    succeeded: bool = True,
    started: datetime = NOW,
    operation: MaintenanceOperation = COMPACTION,
    failed_first: bool = False,
) -> TableMaintenanceRun:
    run = TableMaintenanceRun.create(
        TableMaintenanceRunId.new(), TableId("t-1"), TriggerType.SCHEDULED, [operation], started, execution_ref="wf"
    )
    attempt = 1
    if failed_first:
        run.start_attempt(operation, 1, None, started - timedelta(hours=5))
        run.fail(operation, 1, "boom", started - timedelta(hours=4))
        attempt = 2
    run.start_attempt(operation, attempt, None, started)
    metrics = {} if rewritten is None else {"rewritten_bytes_count": rewritten}
    end = started + timedelta(minutes=minutes)
    if succeeded:
        run.succeed(operation, attempt, metrics, end)
    else:
        run.fail(operation, attempt, "boom", end)
    return run


def test_throughput_is_bytes_over_hours_of_succeeded_compactions():
    """Two compactions, 1 GiB in 30 minutes and 2 GiB in 90 minutes, make 3 GiB over 2 hours."""
    runs = [_run(rewritten=GIB, minutes=30), _run(rewritten=2 * GIB, minutes=90)]
    assert estimate_throughput(runs, default_bytes_per_hour=DEFAULT) == pytest.approx(1.5 * GIB)


def test_throughput_falls_back_to_the_default_without_history():
    """With no succeeded compaction, the default throughput is used."""
    assert estimate_throughput([], default_bytes_per_hour=DEFAULT) == DEFAULT
    assert estimate_throughput([_run(succeeded=False)], default_bytes_per_hour=DEFAULT) == DEFAULT


def test_throughput_ignores_operations_without_bytes_or_duration():
    """A lost callback (no bytes), a compaction that rewrote nothing and a zero duration are left out."""
    runs = [
        _run(rewritten=None),
        _run(rewritten=0),
        _run(minutes=0),
        _run(operation=MaintenanceOperation.EXPIRE_SNAPSHOTS),
    ]
    assert estimate_throughput(runs, default_bytes_per_hour=DEFAULT) == DEFAULT
    assert estimate_throughput([*runs, _run(rewritten=GIB, minutes=60)], default_bytes_per_hour=DEFAULT) == (
        pytest.approx(GIB)
    )


def test_throughput_times_only_the_attempt_that_succeeded():
    """A failed first attempt and the backoff after it do not count as compaction time."""
    run = _run(rewritten=GIB, minutes=60, failed_first=True)
    assert estimate_throughput([run], default_bytes_per_hour=DEFAULT) == pytest.approx(GIB)


def test_throughput_uses_only_the_newest_samples():
    """Only the newest ``max_samples`` compactions count, so the estimate follows recent behaviour."""
    old = [_run(rewritten=GIB, minutes=600, started=NOW - timedelta(days=i + 1)) for i in range(3)]
    new = [_run(rewritten=GIB, minutes=60, started=NOW + timedelta(hours=i)) for i in range(2)]
    assert estimate_throughput([*old, *new], default_bytes_per_hour=DEFAULT, max_samples=2) == pytest.approx(GIB)


def test_default_must_be_positive():
    """A default throughput of zero would make every cost infinite."""
    with pytest.raises(ValueError, match="throughput"):
        estimate_throughput([], default_bytes_per_hour=0)


def test_throughput_ignores_samples_below_the_floor():
    """A compaction that rewrote less than the floor is mostly Spark start-up, so it does not count."""
    runs = [
        _run(rewritten=GIB, minutes=30),
        _run(rewritten=10 * 1024**2, minutes=3, started=NOW + timedelta(hours=1)),
    ]

    throughput = estimate_throughput(runs, default_bytes_per_hour=DEFAULT, min_sample_bytes=64 * 1024**2)

    assert throughput == pytest.approx(2 * GIB)


def test_throughput_falls_back_to_the_default_when_every_sample_is_below_the_floor():
    """With only small compactions in the history, the default throughput is used."""
    runs = [_run(rewritten=10 * 1024**2, minutes=3)]

    assert estimate_throughput(runs, default_bytes_per_hour=DEFAULT, min_sample_bytes=64 * 1024**2) == DEFAULT
