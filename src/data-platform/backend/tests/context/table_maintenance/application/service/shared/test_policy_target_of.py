"""Test policy_target_of: the typed target a port's target fields name."""

from __future__ import annotations

import pytest

from context.table_maintenance.application.domain.model.shared import PolicyTarget, PolicyTargetType
from context.table_maintenance.application.exceptions import ValidationError
from context.table_maintenance.application.service.shared import policy_target_fields, policy_target_of


def test_no_target_is_the_platform_default():
    """No target fields name no target, as the platform default is attached to nothing."""
    assert policy_target_of(None) is None


def test_reads_a_namespace_target():
    """A namespace target's fields read as that target, its path a tuple."""
    target = policy_target_of({"type": "namespace", "path": ["iceberg", "e2e"]})
    assert target == PolicyTarget(type=PolicyTargetType.NAMESPACE, path=("iceberg", "e2e"))


def test_reads_a_table_target_with_its_uuid():
    """A table target keeps its uuid."""
    target = policy_target_of({"type": "table", "path": ["iceberg", "e2e", "orders"], "table_uuid": "u1"})
    assert target == PolicyTarget(type=PolicyTargetType.TABLE, path=("iceberg", "e2e", "orders"), table_uuid="u1")


def test_reads_back_what_policy_target_fields_writes():
    """The fields a service writes for a target read back as the same target."""
    target = PolicyTarget(type=PolicyTargetType.CATALOG, path=("iceberg",))
    assert policy_target_of(policy_target_fields(target)) == target


@pytest.mark.parametrize(
    "raw",
    [
        {"type": "table", "path": ["iceberg", "e2e", "orders"]},
        {"type": "namespace", "path": ["iceberg"]},
        {"type": "warehouse", "path": ["iceberg"]},
        {"path": ["iceberg"]},
    ],
)
def test_refuses_fields_that_name_no_target(raw):
    """Fields that do not make a target are a validation error naming them."""
    with pytest.raises(ValidationError, match="invalid policy target"):
        policy_target_of(raw)
