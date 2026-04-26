"""Test the Tag value object."""

from __future__ import annotations

from base import ValueObject
from core.application.domain.model.catalog.tag import Tag


def test_tag_is_value_object():
    """Tag extends ValueObject."""
    assert issubclass(Tag, ValueObject)


def test_tag_equality():
    """Two Tags with identical fields are equal."""
    a = Tag(name="v1.0", snapshot_id=100, max_ref_age_ms=86400000)
    b = Tag(name="v1.0", snapshot_id=100, max_ref_age_ms=86400000)
    assert a == b


def test_tag_max_ref_age_optional():
    """Tag can have no max_ref_age."""
    t = Tag(name="v1.0", snapshot_id=100)
    assert t.max_ref_age_ms is None
