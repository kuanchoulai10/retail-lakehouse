"""Test the SchemaField and TableSchema value objects."""

from __future__ import annotations

from core.base import ValueObject
from core.application.domain.model.catalog.schema_field import SchemaField
from core.application.domain.model.catalog.table_schema import TableSchema


def test_schema_field_is_value_object():
    """SchemaField extends ValueObject."""
    assert issubclass(SchemaField, ValueObject)


def test_schema_field_equality():
    """Two SchemaFields with the same attributes are equal."""
    a = SchemaField(field_id=1, name="order_id", field_type="long", required=True)
    b = SchemaField(field_id=1, name="order_id", field_type="long", required=True)
    assert a == b


def test_table_schema_is_value_object():
    """TableSchema extends ValueObject."""
    assert issubclass(TableSchema, ValueObject)


def test_table_schema_fields_are_tuple():
    """TableSchema.fields is a tuple of SchemaField."""
    f = SchemaField(field_id=1, name="id", field_type="long", required=True)
    schema = TableSchema(fields=(f,))
    assert isinstance(schema.fields, tuple)
    assert schema.fields[0] == f
