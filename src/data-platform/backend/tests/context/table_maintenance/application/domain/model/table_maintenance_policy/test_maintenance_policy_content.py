"""Test MaintenancePolicyContent."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from context.table_maintenance.application.domain.model.shared import MaintenanceOperation
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    MaintenancePolicyContent,
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
    with pytest.raises(ValidationError):
        MaintenancePolicyContent.from_primitives(wire)


def test_orphan_older_than_below_one_day_is_rejected() -> None:
    """Check the behaviour named by the test."""
    wire = MaintenancePolicyContent.platform_default().to_primitives()
    wire["operations"]["remove_orphan_files"]["execution_policy"]["older_than_seconds"] = 86399
    with pytest.raises(ValidationError):
        MaintenancePolicyContent.from_primitives(wire)


def test_for_operation_returns_each_operation_policy() -> None:
    """Check the behaviour named by the test."""
    operations = MaintenancePolicyContent.platform_default().operations
    assert operations.for_operation(MaintenanceOperation.REWRITE_DATA_FILES) is operations.rewrite_data_files
    assert operations.for_operation(MaintenanceOperation.REWRITE_MANIFESTS) is operations.rewrite_manifests
    assert operations.for_operation(MaintenanceOperation.EXPIRE_SNAPSHOTS) is operations.expire_snapshots
    assert operations.for_operation(MaintenanceOperation.REMOVE_ORPHAN_FILES) is operations.remove_orphan_files
