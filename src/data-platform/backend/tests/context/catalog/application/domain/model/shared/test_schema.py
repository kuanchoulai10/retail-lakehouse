"""Test the Schema and SchemaField value objects on their Pydantic base."""

from __future__ import annotations

import pytest

from base import InvariantViolation
from context.catalog.application.domain.model.shared import Schema, SchemaField

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
        id=7, name="shipping", type="struct<city: required string>", required=False, doc=None, children=(city,)
    )
    element = SchemaField(id=6, name="element", type="string", required=False, doc=None)
    tags = SchemaField(id=5, name="tags", type="list<string>", required=False, doc=None, children=(element,))

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
    ("type_text", "outer"),
    [
        ("struct<a: int>", "struct"),
        ("list<int>", "list"),
        ("map<string, int>", "map"),
        ("decimal(10,2)", "decimal(10,2)"),
        ("long", "long"),
    ],
)
def test_outer_type_of_nested_and_primitive_fields(type_text, outer):
    """A nested type's outer type is its kind; a primitive keeps its own name."""
    assert SchemaField(id=1, name="f", type=type_text, required=False, doc=None).outer_type == outer


def test_children_default_to_none_and_must_be_a_tuple():
    """A field has no children unless given, and a list of children is refused."""
    assert ID.children == ()
    with pytest.raises(InvariantViolation):
        SchemaField(id=1, name="f", type="struct<>", required=False, doc=None, children=[ID])  # ty: ignore[invalid-argument-type]
