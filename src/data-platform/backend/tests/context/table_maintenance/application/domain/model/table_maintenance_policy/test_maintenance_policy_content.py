"""Test MaintenancePolicyContent."""

from __future__ import annotations

from datetime import timedelta

import pytest

from base import InvariantViolation
from context.table_maintenance.application.domain.model.shared import MaintenanceOperation
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    MaintenancePolicyContent,
)
from tests.context.table_maintenance.fakes.default_content_json import DEFAULT_CONTENT_JSON


def test_platform_default_is_the_documented_content() -> None:
    """The platform default is exactly the content the plan documents."""
    assert MaintenancePolicyContent.platform_default().to_primitives() == DEFAULT_CONTENT_JSON


def test_platform_default_round_trips() -> None:
    """The documented content reads back as the platform default."""
    assert MaintenancePolicyContent.from_primitives(DEFAULT_CONTENT_JSON) == MaintenancePolicyContent.platform_default()


def test_a_block_left_out_is_none() -> None:
    """A policy without an operation's block has no spec for that operation."""
    wire = {key: value for key, value in DEFAULT_CONTENT_JSON.items() if key != "expire_snapshots"}
    content = MaintenancePolicyContent.from_primitives(wire)
    assert content.expire_snapshots is None
    assert content.spec_for(MaintenanceOperation.EXPIRE_SNAPSHOTS) is None
    assert content.to_primitives()["expire_snapshots"] is None


def test_a_policy_may_hold_no_block() -> None:
    """A policy with only its triggers does no maintenance at all."""
    content = MaintenancePolicyContent.from_primitives(
        {"description": "nothing", "on": {"schedule": {"every_seconds": 3600}}}
    )
    assert all(content.spec_for(op) is None for op in MaintenanceOperation.ordered())
    assert content.dry_run is False
    assert content.on.catalog_commit is None


def test_spec_for_returns_each_block() -> None:
    """``spec_for`` returns the block of the operation named."""
    content = MaintenancePolicyContent.platform_default()
    assert content.spec_for(MaintenanceOperation.REWRITE_DATA_FILES) is content.rewrite_data_files
    assert content.spec_for(MaintenanceOperation.REWRITE_MANIFESTS) is content.rewrite_manifests
    assert content.spec_for(MaintenanceOperation.EXPIRE_SNAPSHOTS) is content.expire_snapshots
    assert content.spec_for(MaintenanceOperation.REMOVE_ORPHAN_FILES) is content.remove_orphan_files


def test_platform_default_schedule_and_debounce() -> None:
    """The platform default checks hourly and an idle five minutes after a commit."""
    on = MaintenancePolicyContent.platform_default().on
    assert on.schedule.every == timedelta(hours=1)
    assert on.catalog_commit is not None
    assert on.catalog_commit.debounce == timedelta(minutes=5)


def test_old_shape_is_refused() -> None:
    """A content stored in the shape before targets does not load."""
    with pytest.raises(InvariantViolation):
        MaintenancePolicyContent.from_primitives(
            {
                "description": "old",
                "reconcile_interval_seconds": 3600,
                "dry_run": False,
                "operations": {},
            }
        )


@pytest.mark.parametrize("field", ["priority", "reconcile_interval_seconds", "operations"])
def test_a_removed_field_is_refused(field: str) -> None:
    """The removed fields are unknown keys."""
    with pytest.raises(InvariantViolation):
        MaintenancePolicyContent.from_primitives({**DEFAULT_CONTENT_JSON, field: "P2"})


def test_an_option_that_repeats_the_target_is_refused() -> None:
    """``retain_last`` belongs to the target, so it is no option."""
    wire = {
        **DEFAULT_CONTENT_JSON,
        "expire_snapshots": {"target": {"min_snapshots_to_keep": 3}, "options": {"retain_last": 3}},
    }
    with pytest.raises(InvariantViolation):
        MaintenancePolicyContent.from_primitives(wire)


def test_orphan_older_than_below_one_day_is_refused() -> None:
    """Orphan removal never looks at files younger than a day."""
    wire = {**DEFAULT_CONTENT_JSON, "remove_orphan_files": {"target": {"older_than_seconds": 86399}}}
    with pytest.raises(InvariantViolation):
        MaintenancePolicyContent.from_primitives(wire)


def test_a_schedule_is_required() -> None:
    """``on`` without a schedule is refused."""
    with pytest.raises(InvariantViolation):
        MaintenancePolicyContent.from_primitives({**DEFAULT_CONTENT_JSON, "on": {}})
