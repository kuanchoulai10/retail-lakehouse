"""Test the NamespaceId identifier and the Namespace aggregate."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from context.catalog.application.domain.model.namespace import Namespace, NamespaceId


def test_namespace_id_joins_catalog_and_parts_with_the_unit_separator():
    """The value is the catalog then the parts, each joined by U+001F."""
    namespace_id = NamespaceId.of("sales", ("a", "b"))

    assert namespace_id.value == "sales\x1fa\x1fb"
    assert namespace_id.catalog == "sales"
    assert namespace_id.parts == ("a", "b")


def test_namespace_part_with_dot_stays_one_part():
    """A dot is not a separator: ``a.b`` is one part and comes back unchanged."""
    namespace_id = NamespaceId.of("sales", ("a.b",))

    assert namespace_id.parts == ("a.b",)
    assert namespace_id == NamespaceId.of("sales", ("a.b",))
    assert namespace_id != NamespaceId.of("sales", ("a", "b"))


def test_namespace_exposes_catalog_and_parts_of_its_id():
    """The aggregate reads its catalog and parts from its id and keeps its properties."""
    namespace = Namespace(id=NamespaceId.of("sales", ("a", "b c")), properties={"owner": "de"})

    assert (namespace.catalog, namespace.parts, namespace.properties) == ("sales", ("a", "b c"), {"owner": "de"})


def test_namespace_equality_is_by_identity_not_properties():
    """Two copies of the same namespace id are equal whatever their properties."""
    first = Namespace(id=NamespaceId.of("sales", ("raw",)), properties={})
    second = Namespace(id=NamespaceId.of("sales", ("raw",)), properties={"k": "v"})

    assert first == second
    assert first != Namespace(id=NamespaceId.of("sales", ("other",)), properties={})


@pytest.mark.parametrize(
    ("catalog", "parts", "message"),
    [
        ("a\x1fb", ("c",), "catalog name must not contain"),
        ("sales", ("a\x1fb",), "namespace parts must not contain"),
    ],
)
def test_namespace_id_refuses_the_unit_separator_inside_a_catalog_or_part(catalog, parts, message):
    """A U+001F inside the catalog or a part would split into a different namespace, so it is refused."""
    with pytest.raises(ValueError, match=message):
        NamespaceId.of(catalog, parts)


def test_namespace_id_is_built_positionally_and_strict():
    """The id keeps its positional form and takes only a string."""
    assert NamespaceId("sales\x1fraw") == NamespaceId.of("sales", ("raw",))
    with pytest.raises(ValidationError):
        NamespaceId(1)  # ty: ignore[invalid-argument-type]


@pytest.mark.parametrize("value", [{"a": 1}, [("a", "b")], None])
def test_assigning_wrong_properties_is_rejected_and_changes_nothing(value: object):
    """Properties are a map of text to text; a rejected assignment leaves the namespace as it was."""
    namespace = Namespace(id=NamespaceId.of("sales", ("raw",)), properties={"owner": "de"})

    with pytest.raises(ValidationError):
        namespace.properties = value  # ty: ignore[invalid-assignment]

    assert namespace.properties == {"owner": "de"}
