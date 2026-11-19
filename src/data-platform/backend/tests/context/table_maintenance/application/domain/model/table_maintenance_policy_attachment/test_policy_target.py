"""Test the PolicyTarget value object and the attachment aggregate."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    TableMaintenancePolicyId,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy_attachment import (
    PolicyTarget,
    PolicyTargetType,
    TableMaintenancePolicyAttachment,
)
from shared_kernel import prefixed_id_pattern

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def test_table_target_requires_uuid():
    """A table target without a uuid is rejected."""
    with pytest.raises(ValueError, match="table_uuid"):
        PolicyTarget(type=PolicyTargetType.TABLE, path=("c", "n", "t"))


def test_non_table_target_rejects_uuid():
    """A catalog or namespace target must not carry a uuid."""
    with pytest.raises(ValueError, match="table_uuid"):
        PolicyTarget(type=PolicyTargetType.CATALOG, path=("c",), table_uuid="u")


@pytest.mark.parametrize(
    ("type_", "path"),
    [
        (PolicyTargetType.CATALOG, ("c", "n")),
        (PolicyTargetType.CATALOG, ()),
        (PolicyTargetType.NAMESPACE, ("c",)),
    ],
)
def test_path_length_is_checked(type_, path):
    """The path length must suit the target type."""
    with pytest.raises(ValueError, match="path"):
        PolicyTarget(type=type_, path=path)


def test_key_of_table_is_its_uuid_and_survives_rename():
    """A table target is keyed by uuid, whatever its path."""
    a = PolicyTarget(type=PolicyTargetType.TABLE, path=("c", "n", "t"), table_uuid="u-1")
    b = PolicyTarget(type=PolicyTargetType.TABLE, path=("c", "m", "renamed"), table_uuid="u-1")
    assert a.key() == "table:u-1"
    assert a.key() == b.key()


def test_key_of_namespace_joins_the_path():
    """A namespace target is keyed by type and unit-separated path."""
    target = PolicyTarget(type=PolicyTargetType.NAMESPACE, path=("c", "a", "b"))
    assert target.key() == "namespace:c\x1fa\x1fb"


def test_attachment_id_has_the_pa_prefix():
    """Attaching mints a random pa- id, never one derived from the target."""
    target = PolicyTarget(type=PolicyTargetType.CATALOG, path=("c",))
    gold = TableMaintenancePolicyId.new()
    first = TableMaintenancePolicyAttachment.attach(target, gold, NOW)
    second = TableMaintenancePolicyAttachment.attach(target, gold, NOW)
    assert prefixed_id_pattern("pa").fullmatch(first.id.value)
    assert first.id != second.id


def test_attach_and_replace_policy():
    """An attachment records its policy by id and moves to another, keeping its own id."""
    target = PolicyTarget(type=PolicyTargetType.CATALOG, path=("c",))
    gold, silver = TableMaintenancePolicyId.new(), TableMaintenancePolicyId.new()
    attachment = TableMaintenancePolicyAttachment.attach(target, gold, NOW)
    assert attachment.policy_id == gold
    attached_id = attachment.id
    later = datetime(2026, 2, 1, tzinfo=UTC)
    attachment.replace_policy(silver, later)
    assert attachment.policy_id == silver
    assert attachment.attached_at == later
    assert attachment.id == attached_id
