"""Test MaintenancePolicyContent."""

from __future__ import annotations

import pytest

from base import InvariantViolation
from context.table_maintenance.application.domain.model.shared import MaintenanceOperation
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    MaintenancePolicyContent,
    MaintenancePriority,
)


def test_platform_default_round_trips_to_spec_json() -> None:
    """Check the behaviour named by the test."""
    wire = MaintenancePolicyContent.platform_default().to_primitives()
    assert wire["reconcile_interval_seconds"] == 3600
    assert wire["dry_run"] is False
    assert wire["description"] == "Platform default"
    rdf = wire["operations"]["rewrite_data_files"]
    assert rdf["enabled"] is True
    assert rdf["scope"] == {"unit": "partition"}
    assert rdf["trigger_policy"] == {"cooldown_seconds": 3600, "conditions": {"reducible_files": {"at_least": 5}}}
    assert rdf["execution_policy"] == {
        "target_file_size_bytes": None,
        "min_input_files": 2,
        "partial_progress": {"enabled": True, "max_commits": None},
    }
    assert wire["operations"]["rewrite_manifests"]["trigger_policy"]["conditions"] == {
        "small_manifests": {"at_least": 5, "smaller_than_bytes": None}
    }
    assert wire["operations"]["expire_snapshots"]["trigger_policy"] == {
        "cooldown_seconds": 21600,
        "conditions": {"expirable_snapshots": {"at_least": 1}},
    }
    assert wire["operations"]["expire_snapshots"]["execution_policy"] == {
        "older_than_seconds": 86400,
        "retain_last": 10,
    }
    assert wire["operations"]["remove_orphan_files"] == {
        "enabled": True,
        "trigger_policy": {"cooldown_seconds": 604800, "conditions": {}},
        "execution_policy": {"older_than_seconds": 259200},
    }
    assert MaintenancePolicyContent.from_primitives(wire) == MaintenancePolicyContent.platform_default()


def test_condition_of_another_operation_is_rejected() -> None:
    """Check the behaviour named by the test."""
    wire = MaintenancePolicyContent.platform_default().to_primitives()
    wire["operations"]["rewrite_manifests"]["trigger_policy"]["conditions"]["reducible_files"] = {"at_least": 5}
    with pytest.raises(InvariantViolation):
        MaintenancePolicyContent.from_primitives(wire)


def test_orphan_older_than_below_one_day_is_rejected() -> None:
    """Check the behaviour named by the test."""
    wire = MaintenancePolicyContent.platform_default().to_primitives()
    wire["operations"]["remove_orphan_files"]["execution_policy"]["older_than_seconds"] = 86399
    with pytest.raises(InvariantViolation):
        MaintenancePolicyContent.from_primitives(wire)


def test_for_operation_returns_each_operation_policy() -> None:
    """Check the behaviour named by the test."""
    operations = MaintenancePolicyContent.platform_default().operations
    assert operations.for_operation(MaintenanceOperation.REWRITE_DATA_FILES) is operations.rewrite_data_files
    assert operations.for_operation(MaintenanceOperation.REWRITE_MANIFESTS) is operations.rewrite_manifests
    assert operations.for_operation(MaintenanceOperation.EXPIRE_SNAPSHOTS) is operations.expire_snapshots
    assert operations.for_operation(MaintenanceOperation.REMOVE_ORPHAN_FILES) is operations.remove_orphan_files


@pytest.mark.parametrize("seconds", [0, -60])
def test_reconcile_interval_not_positive_is_rejected(seconds: int) -> None:
    """A zero or negative reconcile interval would plan without pause."""
    wire = MaintenancePolicyContent.platform_default().to_primitives()
    wire["reconcile_interval_seconds"] = seconds
    with pytest.raises(InvariantViolation, match="must be positive"):
        MaintenancePolicyContent.from_primitives(wire)


def test_negative_cooldown_is_rejected() -> None:
    """A cooldown cannot be shorter than no cooldown."""
    wire = MaintenancePolicyContent.platform_default().to_primitives()
    wire["operations"]["expire_snapshots"]["trigger_policy"]["cooldown_seconds"] = -1
    with pytest.raises(InvariantViolation, match="must not be negative"):
        MaintenancePolicyContent.from_primitives(wire)


def test_zero_cooldown_means_no_cooldown() -> None:
    """A zero cooldown is allowed."""
    wire = MaintenancePolicyContent.platform_default().to_primitives()
    wire["operations"]["expire_snapshots"]["trigger_policy"]["cooldown_seconds"] = 0
    content = MaintenancePolicyContent.from_primitives(wire)
    assert content.operations.expire_snapshots.trigger_policy.cooldown.total_seconds() == 0


def test_policy_content_without_priority_reads_as_p2() -> None:
    """A policy version stored before priorities existed has no field and reads as P2."""
    wire = MaintenancePolicyContent.platform_default().to_primitives()
    wire.pop("priority", None)
    assert MaintenancePolicyContent.from_primitives(wire).priority is MaintenancePriority.P2


def test_policy_content_round_trips_priority() -> None:
    """A P0 policy is written as "P0" and read back as P0."""
    wire = MaintenancePolicyContent.platform_default().to_primitives()
    wire["priority"] = "P0"
    content = MaintenancePolicyContent.from_primitives(wire)
    assert content.priority is MaintenancePriority.P0
    assert content.to_primitives()["priority"] == "P0"


def test_platform_default_priority_is_p2() -> None:
    """The platform default is the lowest priority."""
    assert MaintenancePolicyContent.platform_default().priority is MaintenancePriority.P2


def test_unknown_priority_is_rejected() -> None:
    """Only P0, P1 and P2 exist."""
    wire = MaintenancePolicyContent.platform_default().to_primitives()
    wire["priority"] = "P3"
    with pytest.raises(InvariantViolation):
        MaintenancePolicyContent.from_primitives(wire)
