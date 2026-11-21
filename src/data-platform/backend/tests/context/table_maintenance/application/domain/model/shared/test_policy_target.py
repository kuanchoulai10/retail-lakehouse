"""Test the PolicyTarget value object."""

from __future__ import annotations

import pytest

from context.table_maintenance.application.domain.model.shared import PolicyTarget, PolicyTargetType


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
