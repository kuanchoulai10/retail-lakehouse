"""Tests for TableReference value object."""

import pytest

from application.domain.model.job import TableReference


def test_stores_fields():
    """Verify that catalog and table are stored correctly."""
    ref = TableReference(catalog="retail", table="inventory.orders")
    assert ref.catalog == "retail"
    assert ref.table == "inventory.orders"


def test_equality_by_value():
    """Verify two TableReferences with the same fields are equal."""
    a = TableReference(catalog="retail", table="orders")
    b = TableReference(catalog="retail", table="orders")
    assert a == b


def test_inequality():
    """Verify two TableReferences with different fields are not equal."""
    a = TableReference(catalog="retail", table="orders")
    b = TableReference(catalog="staging", table="orders")
    assert a != b


def test_is_frozen():
    """Verify TableReference is immutable."""
    ref = TableReference(catalog="retail", table="orders")
    with pytest.raises(AttributeError):
        ref.catalog = "other"  # type: ignore[misc]  # ty: ignore[invalid-assignment]
