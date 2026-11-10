"""Test the Schema and SchemaField value objects on their Pydantic base."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

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
    with pytest.raises(ValidationError):
        build()


def test_schema_and_field_are_immutable():
    """Neither a schema nor a field changes in place."""
    with pytest.raises(ValidationError):
        ID.name = "other"
    with pytest.raises(ValidationError):
        Schema(schema_id=0, fields=()).schema_id = 1
