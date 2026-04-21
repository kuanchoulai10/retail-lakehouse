"""Test the TableId value object."""

from __future__ import annotations

from base import EntityId
from application.domain.model.catalog.table_id import TableId


def test_table_id_is_entity_id():
    """Verify TableId extends EntityId."""
    assert issubclass(TableId, EntityId)


def test_table_id_equality():
    """Two TableIds with the same value are equal."""
    assert TableId(value="default.orders") == TableId(value="default.orders")


def test_table_id_inequality():
    """Different values are not equal."""
    assert TableId(value="a.b") != TableId(value="c.d")


def test_table_id_str():
    """str() returns the raw identifier."""
    assert str(TableId(value="default.orders")) == "default.orders"
