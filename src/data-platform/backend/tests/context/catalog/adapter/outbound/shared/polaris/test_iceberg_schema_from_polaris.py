"""Test mapping an Iceberg REST schema to a Schema: nested fields keep their ids and kinds at every depth."""

from __future__ import annotations

from context.catalog.adapter.outbound.shared.polaris import iceberg_schema_from_polaris
from context.catalog.application.port.outbound.shared import Schema, SchemaFieldKind

STRUCT_IN_LIST = {
    "id": 1,
    "name": "lines",
    "required": False,
    "type": {
        "type": "list",
        "element-id": 2,
        "element-required": True,
        "element": {
            "type": "struct",
            "fields": [
                {"id": 3, "name": "sku", "required": True, "type": "string"},
                {"id": 4, "name": "qty", "required": False, "type": "int"},
            ],
        },
    },
}
LIST_OF_LIST = {
    "id": 5,
    "name": "matrix",
    "required": False,
    "type": {
        "type": "list",
        "element-id": 6,
        "element-required": False,
        "element": {"type": "list", "element-id": 7, "element-required": True, "element": "double"},
    },
}
MAP_WITH_STRUCT_KEY = {
    "id": 8,
    "name": "prices",
    "required": False,
    "type": {
        "type": "map",
        "key-id": 9,
        "key": {"type": "struct", "fields": [{"id": 11, "name": "region", "required": True, "type": "string"}]},
        "value-id": 10,
        "value-required": False,
        "value": "decimal(10,2)",
    },
}


def _schema() -> Schema:
    return iceberg_schema_from_polaris(
        {"type": "struct", "schema-id": 3, "fields": [STRUCT_IN_LIST, LIST_OF_LIST, MAP_WITH_STRUCT_KEY]}
    )


def test_nested_fields_walk_with_their_full_paths_and_ids():
    """A struct in a list, a list of lists and a map with a struct key walk depth first with their own ids."""
    assert [(walked.path, walked.field.id) for walked in _schema().walk()] == [
        (("lines",), 1),
        (("lines", "element"), 2),
        (("lines", "element", "sku"), 3),
        (("lines", "element", "qty"), 4),
        (("matrix",), 5),
        (("matrix", "element"), 6),
        (("matrix", "element", "element"), 7),
        (("prices",), 8),
        (("prices", "key"), 9),
        (("prices", "key", "region"), 11),
        (("prices", "value"), 10),
    ]


def test_each_field_carries_the_kind_of_its_type():
    """The kind comes from the JSON type object: struct, list or map, and primitive for a type name."""
    assert [(walked.field.id, walked.field.kind) for walked in _schema().walk()] == [
        (1, SchemaFieldKind.LIST),
        (2, SchemaFieldKind.STRUCT),
        (3, SchemaFieldKind.PRIMITIVE),
        (4, SchemaFieldKind.PRIMITIVE),
        (5, SchemaFieldKind.LIST),
        (6, SchemaFieldKind.LIST),
        (7, SchemaFieldKind.PRIMITIVE),
        (8, SchemaFieldKind.MAP),
        (9, SchemaFieldKind.STRUCT),
        (11, SchemaFieldKind.PRIMITIVE),
        (10, SchemaFieldKind.PRIMITIVE),
    ]


def test_outer_types_follow_the_kinds():
    """A nested field's outer type is its kind; a primitive's is its type name."""
    assert [walked.field.outer_type for walked in _schema().walk()] == [
        "list",
        "struct",
        "string",
        "int",
        "list",
        "list",
        "double",
        "map",
        "struct",
        "string",
        "decimal(10,2)",
    ]
