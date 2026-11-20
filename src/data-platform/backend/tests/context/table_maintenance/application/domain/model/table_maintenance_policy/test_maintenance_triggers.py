"""Test the ``on:`` trigger value objects."""

from __future__ import annotations

from datetime import timedelta

import pytest

from base import InvariantViolation
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    CatalogCommitTrigger,
    MaintenanceTriggers,
    ScheduleTrigger,
)


def test_schedule_reads_every_seconds() -> None:
    """Check the wire name of the schedule interval."""
    assert ScheduleTrigger.from_primitives({"every_seconds": 300}).every == timedelta(minutes=5)


def test_schedule_writes_every_seconds() -> None:
    """Check the schedule is written back under its wire name."""
    assert ScheduleTrigger(every=timedelta(hours=1)).to_primitives() == {"every_seconds": 3600}


@pytest.mark.parametrize("seconds", [0, 59, 604801])
def test_schedule_out_of_range_is_refused(seconds: int) -> None:
    """Check an interval under a minute or over a week is refused."""
    with pytest.raises(InvariantViolation, match="must be between 60 and 604800 seconds"):
        ScheduleTrigger.from_primitives({"every_seconds": seconds})


@pytest.mark.parametrize("seconds", [60, 604800])
def test_schedule_bounds_are_allowed(seconds: int) -> None:
    """Check both ends of the range are allowed."""
    assert ScheduleTrigger.from_primitives({"every_seconds": seconds}).every == timedelta(seconds=seconds)


def test_schedule_is_required() -> None:
    """Check triggers without a schedule are refused."""
    with pytest.raises(InvariantViolation):
        MaintenanceTriggers.from_primitives({"catalog_commit": {"debounce_seconds": 60}})


def test_catalog_commit_defaults_to_five_minutes() -> None:
    """Check an empty catalog commit trigger debounces five minutes."""
    triggers = MaintenanceTriggers.from_primitives({"schedule": {"every_seconds": 3600}, "catalog_commit": {}})
    assert triggers.catalog_commit is not None
    assert triggers.catalog_commit.debounce == timedelta(minutes=5)


def test_no_catalog_commit_means_none() -> None:
    """Check leaving catalog commit out means commits do not trigger a check."""
    assert MaintenanceTriggers.from_primitives({"schedule": {"every_seconds": 3600}}).catalog_commit is None


def test_zero_debounce_is_allowed() -> None:
    """Check a debounce of zero is allowed."""
    assert CatalogCommitTrigger.from_primitives({"debounce_seconds": 0}).debounce == timedelta(0)


def test_debounce_over_a_day_is_refused() -> None:
    """Check a debounce over a day is refused."""
    with pytest.raises(InvariantViolation, match="must be between 0 and 86400 seconds"):
        CatalogCommitTrigger.from_primitives({"debounce_seconds": 86401})


def test_debounce_of_a_day_is_allowed() -> None:
    """Check a debounce of exactly a day is allowed."""
    assert CatalogCommitTrigger.from_primitives({"debounce_seconds": 86400}).debounce == timedelta(days=1)


def test_negative_debounce_is_refused() -> None:
    """Check a negative debounce is refused."""
    with pytest.raises(InvariantViolation):
        CatalogCommitTrigger.from_primitives({"debounce_seconds": -1})


def test_triggers_round_trip() -> None:
    """Check triggers survive the wire."""
    data = {"schedule": {"every_seconds": 3600}, "catalog_commit": {"debounce_seconds": 300}}
    assert MaintenanceTriggers.from_primitives(data).to_primitives() == data
