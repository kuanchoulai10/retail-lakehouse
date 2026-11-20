"""Test the Schema and SchemaField value objects on their Pydantic base."""

from __future__ import annotations

import pytest

from base import InvariantViolation
from context.catalog.application.domain.model.shared import Schema, SchemaField, SchemaFieldKind

ID = SchemaField(id=1, name="id", type="long", required=True, doc=None)


def test_field_named_finds_a_top_level_field():
    """A field is found by its name; an unknown name is None."""
    schema = Schema(schema_id=0, fields=(ID,))

    assert schema.field_named("id") == ID
    assert schema.field_named("nope") is None


@pytest.mark.parametrize(
    "build",
    [
        lambda: Schema(schema_id=0, fields=[ID]),  # ty: ignore[invalid-argument-type]
        lambda: Schema(schema_id="0", fields=()),  # ty: ignore[invalid-argument-type]
        lambda: SchemaField(id=1, name="id", type="long", required=1, doc=None),  # ty: ignore[invalid-argument-type]
        lambda: SchemaField(id=1, name="id", type="long", required=True),  # ty: ignore[missing-argument]
    ],
)
def test_construction_is_strict(build):
    """A list is no tuple, a string no int, an int no bool, and ``doc`` must be given."""
    with pytest.raises(InvariantViolation):
        build()


def test_schema_and_field_are_immutable():
    """Neither a schema nor a field changes in place."""
    with pytest.raises(AttributeError, match="is immutable"):
        ID.name = "other"
    with pytest.raises(AttributeError, match="is immutable"):
        Schema(schema_id=0, fields=()).schema_id = 1


def test_walk_lists_nested_fields_after_their_parent():
    """Every field is listed depth first, a field before its children, with its path and depth."""
    city = SchemaField(id=8, name="city", type="string", required=True, doc=None)
    shipping = SchemaField(
        id=7,
        name="shipping",
        type="struct<city: required string>",
        required=False,
        doc=None,
        kind=SchemaFieldKind.STRUCT,
        children=(city,),
    )
    element = SchemaField(id=6, name="element", type="string", required=False, doc=None)
    tags = SchemaField(
        id=5, name="tags", type="list<string>", required=False, doc=None, kind=SchemaFieldKind.LIST, children=(element,)
    )

    walked = Schema(schema_id=1, fields=(tags, shipping)).walk()

    assert [(w.path, w.depth, w.field.id) for w in walked] == [
        (("tags",), 0, 5),
        (("tags", "element"), 1, 6),
        (("shipping",), 0, 7),
        (("shipping", "city"), 1, 8),
    ]


def test_walk_of_a_schema_without_nested_fields_is_its_top_level_fields():
    """A flat schema walks to one entry per field, each at depth 0."""
    assert [(w.path, w.depth) for w in Schema(schema_id=0, fields=(ID,)).walk()] == [(("id",), 0)]


@pytest.mark.parametrize(
    ("kind", "type_text", "outer"),
    [
        (SchemaFieldKind.STRUCT, "struct<a: int>", "struct"),
        (SchemaFieldKind.LIST, "list<int>", "list"),
        (SchemaFieldKind.MAP, "map<string, int>", "map"),
        (SchemaFieldKind.PRIMITIVE, "decimal(10,2)", "decimal(10,2)"),
        (SchemaFieldKind.PRIMITIVE, "long", "long"),
    ],
)
def test_outer_type_of_nested_and_primitive_fields(kind, type_text, outer):
    """A nested field's outer type is its kind, whatever its text; a primitive keeps its own name."""
    field = SchemaField(id=1, name="f", type=type_text, required=False, doc=None, kind=kind)
    assert field.outer_type == outer


def test_outer_type_follows_the_kind_not_the_text():
    """The outer type is read from the kind, so a text that only looks nested stays a primitive name."""
    assert SchemaField(id=1, name="f", type="struct<odd", required=False, doc=None).outer_type == "struct<odd"
    assert SchemaField(id=1, name="f", type="", required=False, doc=None, kind=SchemaFieldKind.MAP).outer_type == "map"


def test_kind_defaults_to_primitive_and_must_be_the_enum():
    """A field is primitive unless given a kind, and a plain string is not a kind."""
    assert ID.kind is SchemaFieldKind.PRIMITIVE
    with pytest.raises(InvariantViolation):
        SchemaField(id=1, name="f", type="list<int>", required=False, doc=None, kind="list")  # ty: ignore[invalid-argument-type]


def test_a_primitive_field_has_no_children():
    """Only a struct, list or map holds nested fields."""
    with pytest.raises(InvariantViolation, match="primitive"):
        SchemaField(id=1, name="f", type="long", required=False, doc=None, children=(ID,))


def test_children_default_to_an_empty_tuple_and_must_be_a_tuple():
    """A field has no children unless given, and a list of children is refused."""
    assert ID.children == ()
    with pytest.raises(InvariantViolation):
        SchemaField(
            id=1,
            name="f",
            type="struct<>",
            required=False,
            doc=None,
            kind=SchemaFieldKind.STRUCT,
            children=[ID],  # ty: ignore[invalid-argument-type]
        )
