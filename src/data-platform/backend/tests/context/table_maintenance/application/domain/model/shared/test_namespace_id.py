"""Test the NamespaceId identifier: a catalog and its namespace levels, and the namespaces enclosing a table."""

from __future__ import annotations

import pytest

from base import InvariantViolation
from context.table_maintenance.application.domain.model.shared import CatalogId, NamespaceId


def test_of_joins_the_catalog_and_the_levels_with_the_unit_separator():
    """The id's value is the catalog and the levels joined by U+001F, so a dot inside a level stays one level."""
    namespace_id = NamespaceId.of("iceberg", ("sales", "eu.west"))
    assert namespace_id.value == "iceberg\x1fsales\x1feu.west"
    assert namespace_id.catalog == "iceberg"
    assert namespace_id.levels == ("sales", "eu.west")


def test_equal_catalogs_and_levels_give_equal_ids():
    """Two ids of one namespace are equal, and the namespace of another catalog is another id."""
    assert NamespaceId.of("iceberg", ("sales",)) == NamespaceId.of("iceberg", ("sales",))
    assert NamespaceId.of("iceberg", ("sales",)) != NamespaceId.of("lake", ("sales",))


@pytest.mark.parametrize(
    ("catalog", "levels"),
    [
        ("", ("sales",)),
        ("iceberg", ()),
        ("iceberg", ("",)),
        ("iceberg", ("sales", "")),
        ("ice\x1fberg", ("sales",)),
        ("iceberg", ("sa\x1fles",)),
    ],
)
def test_of_refuses_an_empty_part_or_a_unit_separator(catalog: str, levels: tuple[str, ...]):
    """A namespace id needs a catalog and at least one level, none of them empty or holding U+001F."""
    with pytest.raises(ValueError, match="U\\+001F|a catalog and at least one level"):
        NamespaceId.of(catalog, levels)


def test_a_raw_value_without_a_level_is_refused():
    """A value built directly must hold a catalog and a level too."""
    with pytest.raises(InvariantViolation, match="a catalog and at least one level"):
        NamespaceId("iceberg")


def test_enclosing_runs_from_the_deepest_namespace_to_the_top_level():
    """The namespaces enclosing a table run from its own namespace up to the top-level one."""
    assert NamespaceId.enclosing("c", "a.b") == (NamespaceId.of("c", ("a", "b")), NamespaceId.of("c", ("a",)))


def test_enclosing_a_top_level_namespace_is_that_namespace():
    """A table in a top-level namespace is enclosed by that namespace alone."""
    assert NamespaceId.enclosing("c", "a") == (NamespaceId.of("c", ("a",)),)


def test_enclosing_no_namespace_is_nothing():
    """A table name with an empty namespace is enclosed by no namespace."""
    assert NamespaceId.enclosing("c", "") == ()


def test_a_catalog_id_is_the_catalog_name():
    """A catalog is identified by its name, unprefixed."""
    assert CatalogId("iceberg").value == "iceberg"
    assert CatalogId.PREFIX is None
    assert NamespaceId.PREFIX is None
