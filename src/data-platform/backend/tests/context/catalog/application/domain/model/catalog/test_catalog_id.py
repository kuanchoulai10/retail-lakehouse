"""Test the CatalogId identifier."""

from __future__ import annotations

import pytest

from context.catalog.application.domain.model.catalog import CatalogId


def test_catalog_id_is_the_catalog_name():
    """The value and the name are the catalog name."""
    catalog_id = CatalogId.of("sales")

    assert (catalog_id.value, catalog_id.name) == ("sales", "sales")


def test_catalog_name_with_the_unit_separator_is_refused():
    """U+001F joins a catalog to its namespace parts in child ids, so a name cannot hold it."""
    with pytest.raises(ValueError, match="catalog name must not contain the unit separator U\\+001F"):
        CatalogId.of("a\x1fb")
