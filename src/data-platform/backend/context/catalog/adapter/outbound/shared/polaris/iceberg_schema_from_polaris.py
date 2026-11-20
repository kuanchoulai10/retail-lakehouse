"""Define the iceberg_schema_from_polaris function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.catalog.adapter.outbound.shared.polaris.iceberg_type_from_polaris import (
    iceberg_type_from_polaris,
)
from context.catalog.adapter.outbound.shared.polaris.polaris_integer import polaris_integer
from context.catalog.adapter.outbound.shared.polaris.polaris_text import polaris_text
from context.catalog.application.port.outbound.shared import Schema, SchemaField

if TYPE_CHECKING:
    from collections.abc import Mapping


def _required(value: object) -> bool:
    if value is None:
        return False
    if not isinstance(value, bool):
        raise TypeError(f"schema field required must be true or false, not {value!r}")
    return value


def _child(field_id: object, name: str, iceberg_type: str | dict[str, Any], required: object) -> SchemaField:
    return SchemaField(
        id=polaris_integer(field_id, f"schema {name} id"),
        name=name,
        type=iceberg_type_from_polaris(iceberg_type),
        required=_required(required),
        doc=None,
        children=_children(iceberg_type),
    )


def _children(iceberg_type: str | dict[str, Any]) -> tuple[SchemaField, ...]:
    if isinstance(iceberg_type, str):
        return ()
    kind = iceberg_type.get("type")
    if kind == "struct":
        return tuple(_field(field) for field in iceberg_type.get("fields", []))
    if kind == "list":
        return (
            _child(
                iceberg_type["element-id"], "element", iceberg_type["element"], iceberg_type.get("element-required")
            ),
        )
    if kind == "map":
        return (
            _child(iceberg_type["key-id"], "key", iceberg_type["key"], True),
            _child(iceberg_type["value-id"], "value", iceberg_type["value"], iceberg_type.get("value-required")),
        )
    return ()


def _field(field: Mapping[str, Any]) -> SchemaField:
    return SchemaField(
        id=polaris_integer(field["id"], "schema field id"),
        name=polaris_text(field["name"], "schema field name"),
        type=iceberg_type_from_polaris(field["type"]),
        required=_required(field.get("required")),
        doc=field.get("doc"),
        children=_children(field["type"]),
    )


def iceberg_schema_from_polaris(schema: Mapping[str, Any]) -> Schema:
    """Map one Iceberg REST schema struct to a Schema: its id and its top-level fields in order.

    A missing ``schema-id`` is 0 and a missing or null ``required`` is false. Nothing is coerced:
    an id that is not an integer, a name that is not text or a ``required`` that is not a bool
    raises TypeError. Types are rendered as text by ``iceberg_type_from_polaris``; a nested type's
    fields, a list's element and a map's key and value become ``children`` with their own ids.
    """
    fields = schema["fields"]
    if not isinstance(fields, list):
        raise TypeError(f"schema fields must be a list, not {fields!r}")
    return Schema(
        schema_id=polaris_integer(schema.get("schema-id", 0), "schema-id"),
        fields=tuple(_field(field) for field in fields),
    )
