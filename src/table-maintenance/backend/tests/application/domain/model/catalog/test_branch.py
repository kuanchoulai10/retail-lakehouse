"""Test the Branch entity and RetentionPolicy value object."""

from __future__ import annotations

from base import Entity, EntityId, ValueObject
from core.application.domain.model.catalog.branch import Branch
from core.application.domain.model.catalog.branch_id import BranchId
from core.application.domain.model.catalog.retention_policy import RetentionPolicy


def test_branch_id_is_entity_id():
    """BranchId extends EntityId."""
    assert issubclass(BranchId, EntityId)


def test_retention_policy_is_value_object():
    """RetentionPolicy extends ValueObject."""
    assert issubclass(RetentionPolicy, ValueObject)


def test_branch_is_entity():
    """Branch extends Entity, not AggregateRoot."""
    assert issubclass(Branch, Entity)


def test_branch_equality_by_id():
    """Two Branches with the same BranchId are equal regardless of snapshot_id."""
    a = Branch(id=BranchId(value="main"), snapshot_id=100)
    b = Branch(id=BranchId(value="main"), snapshot_id=200)
    assert a == b


def test_branch_inequality():
    """Different BranchId means not equal."""
    a = Branch(id=BranchId(value="main"), snapshot_id=100)
    b = Branch(id=BranchId(value="audit"), snapshot_id=100)
    assert a != b


def test_branch_retention_optional():
    """Branch can have no retention policy."""
    b = Branch(id=BranchId(value="main"), snapshot_id=1)
    assert b.retention is None


def test_branch_with_retention():
    """Branch stores retention policy."""
    r = RetentionPolicy(
        max_snapshot_age_ms=86400000, max_ref_age_ms=None, min_snapshots_to_keep=5
    )
    b = Branch(id=BranchId(value="main"), snapshot_id=1, retention=r)
    assert b.retention is not None
    assert b.retention.max_snapshot_age_ms == 86400000
    assert b.retention.min_snapshots_to_keep == 5
