"""Test the TableMaintenancePolicy aggregate."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from base import InvariantViolation
from context.table_maintenance.application.domain.model.shared import TableMaintenancePolicyId
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    DEFAULT_POLICY_ID,
    DEFAULT_POLICY_NAME,
    MaintenancePolicyContent,
    StalePolicyVersion,
    TableMaintenancePolicy,
    TableMaintenancePolicyName,
)
from tests.context.table_maintenance.id_shape import IdShape

T0 = datetime(2026, 1, 1, tzinfo=UTC)
T1 = T0 + timedelta(hours=1)


def make(name: str = "gold") -> TableMaintenancePolicy:
    """Build a policy at version 1."""
    return TableMaintenancePolicy.create(
        TableMaintenancePolicyName(value=name), MaintenancePolicyContent.platform_default(), T0
    )


def test_create_starts_at_version_one():
    """A new policy is version 1 with equal timestamps."""
    policy = make()
    assert policy.version == 1
    assert policy.created_at == policy.updated_at == T0


def test_policy_gets_an_mp_id_on_create():
    """A new policy gets a random ``mp-`` id of its own and keeps its name beside it."""
    first, second = make("gold"), make("gold")

    assert IdShape(TableMaintenancePolicyId).fullmatch(first.id.value)
    assert first.id != second.id
    assert first.name == TableMaintenancePolicyName(value="gold")


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


def test_current_version_points_at_the_policy_id():
    """A version record belongs to its policy by id, not by name."""
    policy = make()

    assert policy.current_version().policy_id == policy.id


def test_replace_with_stale_version_raises():
    """A stale expected version is rejected and nothing changes."""
    policy = make()
    with pytest.raises(StalePolicyVersion):
        policy.replace(MaintenancePolicyContent.platform_default(), expected_version=2, now=T1)
    assert policy.version == 1


def test_default_policy_has_the_fixed_id():
    """The default policy has the fixed id ``mp-00000000000000000000000000``, its name and the platform content."""
    policy = TableMaintenancePolicy.create_default(T0)

    assert DEFAULT_POLICY_ID == TableMaintenancePolicyId("mp-00000000000000000000000000")
    assert policy.id == DEFAULT_POLICY_ID
    assert policy.name.value == DEFAULT_POLICY_NAME
    assert policy.content == MaintenancePolicyContent.platform_default()
    assert policy.version == 1


def test_is_default():
    """The default is told by its fixed id: another policy named default is not it."""
    assert TableMaintenancePolicy.create_default(T0).is_default
    assert not make(DEFAULT_POLICY_NAME).is_default
    assert not make("gold").is_default


def test_policy_id_refuses_another_shape():
    """A policy id must look like ``mp-<26 base32 characters>``; a name is not an id."""
    with pytest.raises(InvariantViolation, match="TableMaintenancePolicyId must look like mp-"):
        TableMaintenancePolicyId("gold")


@pytest.mark.parametrize("name", ["has space", "", "x" * 65, "a/b"])
def test_invalid_name_is_rejected(name: str):
    """A name outside the pattern is rejected."""
    with pytest.raises(InvariantViolation):
        TableMaintenancePolicyName(value=name)


@pytest.mark.parametrize(
    "name", ["mp-00000000000000000000000000", "mp-01kaa4zc9qf3v8d2m6xk0w7b1n", "rc-00000000000000000000000001"]
)
def test_a_name_shaped_like_a_prefixed_id_is_rejected(name: str):
    """A name that reads as an id (``mp-…`` or any other prefix) is refused, so names and ids never mix."""
    with pytest.raises(InvariantViolation, match="must not look like a prefixed id"):
        TableMaintenancePolicyName(value=name)


@pytest.mark.parametrize(
    "name", ["mp-nightly", "nightly-v2-01kaa4zc9qf3v8d2m6xk0w7b1n", "MP-00000000000000000000000000"]
)
def test_a_name_that_only_resembles_an_id_is_accepted(name: str):
    """Only the exact id shape is refused; a name that merely starts with a prefix stays valid."""
    assert TableMaintenancePolicyName(value=name).value == name
