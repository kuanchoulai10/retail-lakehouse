"""Test the TableMaintenancePolicy aggregate."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    DEFAULT_POLICY_NAME,
    MaintenancePolicyContent,
    StalePolicyVersion,
    TableMaintenancePolicy,
    TableMaintenancePolicyName,
)

T0 = datetime(2026, 1, 1, tzinfo=UTC)
T1 = T0 + timedelta(hours=1)


def make(name: str = "gold") -> TableMaintenancePolicy:
    """Build a policy at version 1."""
    return TableMaintenancePolicy.create(
        TableMaintenancePolicyName(name), MaintenancePolicyContent.platform_default(), T0
    )


def test_create_starts_at_version_one():
    """A new policy is version 1 with equal timestamps."""
    policy = make()
    assert policy.version == 1
    assert policy.created_at == policy.updated_at == T0


def test_replace_increments_version():
    """Replacing with the current version bumps it and the update time."""
    policy = make()
    content = MaintenancePolicyContent.platform_default().model_copy(update={"dry_run": True})
    policy.replace(content, expected_version=1, now=T1)
    assert policy.version == 2
    assert policy.content.dry_run is True
    assert policy.updated_at == T1
    assert policy.current_version().version == 2
    assert policy.current_version().created_at == T1


def test_replace_with_stale_version_raises():
    """A stale expected version is rejected and nothing changes."""
    policy = make()
    with pytest.raises(StalePolicyVersion):
        policy.replace(MaintenancePolicyContent.platform_default(), expected_version=2, now=T1)
    assert policy.version == 1


def test_is_default():
    """Only the policy named default is the default."""
    assert make(DEFAULT_POLICY_NAME).is_default
    assert not make("gold").is_default


@pytest.mark.parametrize("name", ["has space", "", "x" * 65, "a/b"])
def test_invalid_name_is_rejected(name: str):
    """A name outside the pattern is rejected."""
    with pytest.raises(ValidationError):
        TableMaintenancePolicyName(name)
