"""Test how a table's properties are resolved against Iceberg's and the catalog's defaults."""

from __future__ import annotations

import pytest

from context.catalog.application.domain.model.catalog import (
    Catalog,
    CatalogId,
    CatalogType,
    StorageConfig,
    StorageType,
)
from context.catalog.application.domain.model.shared import Schema, SchemaField
from context.catalog.application.domain.model.table import (
    PartitionSpec,
    SortOrder,
    Table,
    TableId,
    TableProperty,
    TablePropertyCatalogue,
    TablePropertyDefaultSource,
    TablePropertyDefinition,
)
from context.catalog.application.domain.service.table import resolve_table_properties

CATALOGUE = TablePropertyCatalogue(
    iceberg_version="1.10.1",
    definitions=(
        TablePropertyDefinition(
            key="format-version", iceberg_default="2", description="Format version.", resettable=False
        ),
        TablePropertyDefinition(key="write.format.default", iceberg_default="parquet", description="Format."),
        TablePropertyDefinition(
            key="write.parquet.compression-codec",
            iceberg_default="zstd",
            description="Codec.",
            written_on_create=True,
        ),
        TablePropertyDefinition(key="write.data.path", iceberg_default=None, description="Data path."),
        TablePropertyDefinition(key="gc.enabled", iceberg_default="true", description="GC.", resettable=False),
        TablePropertyDefinition(
            key="created-at",
            iceberg_default=None,
            description="Created.",
            resettable=False,
            set_by_catalog=True,
        ),
    ),
)


def _table(properties: dict[str, str], format_version: int | None = 2) -> Table:
    return Table(
        id=TableId.of("sales", ("retail",), "orders"),
        uuid="u-1",
        format_version=format_version,
        location="s3://w/retail/orders",
        current_snapshot_id=None,
        last_updated_ms=1,
        current_schema=Schema(
            schema_id=0, fields=(SchemaField(id=1, name="id", type="long", required=True, doc=None),)
        ),
        partition_spec=PartitionSpec.unpartitioned(),
        sort_order=SortOrder.unsorted(),
        properties=properties,
    )


def _catalog(properties: dict[str, str] | None = None) -> Catalog:
    return Catalog(
        id=CatalogId.of("sales"),
        type=CatalogType.INTERNAL,
        properties={"default-base-location": "s3://w", **(properties or {})},
        storage_config=StorageConfig(storage_type=StorageType.S3, allowed_locations=("s3://w",)),
    )


def _by_key(rows: list[TableProperty]) -> dict[str, TableProperty]:
    return {row.key: row for row in rows}


def test_every_known_key_is_listed_with_iceberg_default_when_the_catalog_sets_none():
    """An unset known key shows Iceberg's default, is not modified and is resettable as the catalogue says."""
    rows = _by_key(resolve_table_properties(_table({}), _catalog(), CATALOGUE))

    row = rows["write.format.default"]
    assert (row.current_value, row.default_value, row.default_source) == (None, "parquet", "iceberg")
    assert (row.modified, row.custom, row.resettable, row.description) == (False, False, True, "Format.")
    assert rows["gc.enabled"].resettable is False


def test_rows_are_ordered_by_key():
    """The rows come sorted by key, custom and known alike."""
    rows = resolve_table_properties(_table({"owner": "x"}), _catalog(), CATALOGUE)
    keys = [row.key for row in rows]
    assert keys == sorted(keys)


def test_a_key_set_to_a_different_value_is_modified():
    """A set key whose value differs from the default is modified; the same value is not."""
    rows = _by_key(
        resolve_table_properties(
            _table({"write.format.default": "orc", "write.parquet.compression-codec": "zstd"}), _catalog(), CATALOGUE
        )
    )

    assert rows["write.format.default"].modified is True
    assert rows["write.parquet.compression-codec"].modified is False


def test_a_set_key_without_a_default_is_modified():
    """A known key Iceberg has no default for is modified as soon as it is set."""
    rows = _by_key(resolve_table_properties(_table({"write.data.path": "s3://w/d"}), _catalog(), CATALOGUE))

    row = rows["write.data.path"]
    assert (row.default_value, row.default_source, row.modified) == (None, "iceberg", True)


def test_format_version_comes_from_the_table_metadata():
    """Iceberg keeps the format version out of the properties; the row reads the table's own version."""
    rows = _by_key(resolve_table_properties(_table({}, format_version=3), _catalog(), CATALOGUE))

    row = rows["format-version"]
    assert (row.current_value, row.default_value, row.modified, row.resettable) == ("3", "2", True, False)


def test_catalog_table_default_is_the_default_with_source_catalog():
    """``table-default.<key>`` on the catalog is the default shown, labelled catalog."""
    catalog = _catalog({"table-default.write.format.default": "orc"})
    rows = _by_key(resolve_table_properties(_table({"write.format.default": "orc"}), catalog, CATALOGUE))

    row = rows["write.format.default"]
    assert (row.default_value, row.default_source, row.modified, row.resettable) == ("orc", "catalog", False, True)


def test_catalog_table_override_forces_the_key_and_refuses_a_reset():
    """``table-override.<key>`` wins over every default, is labelled catalog_override and is not resettable."""
    catalog = _catalog({"table-default.write.format.default": "avro", "table-override.write.format.default": "orc"})
    rows = _by_key(resolve_table_properties(_table({"write.format.default": "parquet"}), catalog, CATALOGUE))

    row = rows["write.format.default"]
    assert (row.default_value, row.default_source) == ("orc", TablePropertyDefaultSource.CATALOG_OVERRIDE)
    assert (row.modified, row.resettable) == (True, False)


def test_a_custom_key_is_listed_modified_without_a_default():
    """A key the catalogue does not know is custom, modified, deletable and has no default or description."""
    rows = _by_key(resolve_table_properties(_table({"owner": "data-eng"}), _catalog(), CATALOGUE))

    row = rows["owner"]
    assert (row.current_value, row.default_value, row.default_source, row.description) == (
        "data-eng",
        None,
        None,
        None,
    )
    assert (row.custom, row.modified, row.resettable) == (True, True, True)


def test_a_key_only_the_catalog_names_is_listed_as_custom_with_the_catalog_default():
    """A custom key the catalog defaults is listed even when unset.

    Unset, the catalog default does not apply, so the row is modified.
    """
    rows = _by_key(resolve_table_properties(_table({}), _catalog({"table-default.owner": "data-eng"}), CATALOGUE))

    row = rows["owner"]
    assert (row.current_value, row.default_value, row.default_source) == (None, "data-eng", "catalog")
    assert (row.custom, row.modified, row.reset_value()) == (True, True, "data-eng")


@pytest.mark.parametrize(
    ("key", "properties", "catalog_properties", "expected"),
    [
        ("write.format.default", {"write.format.default": "orc"}, {}, None),
        ("write.parquet.compression-codec", {"write.parquet.compression-codec": "gzip"}, {}, "zstd"),
        (
            "write.format.default",
            {"write.format.default": "parquet"},
            {"table-default.write.format.default": "orc"},
            "orc",
        ),
        ("owner", {"owner": "x"}, {}, None),
    ],
)
def test_reset_value_removes_the_key_or_writes_what_a_new_table_gets(
    key: str, properties: dict[str, str], catalog_properties: dict[str, str], expected: str | None
):
    """A reset removes the key, unless a new table would hold it explicitly: then it writes that value."""
    rows = _by_key(resolve_table_properties(_table(properties), _catalog(catalog_properties), CATALOGUE))

    assert rows[key].reset_value() == expected


def test_a_custom_key_at_its_catalog_default_is_not_modified():
    """A custom key set to the catalog's table-default is at its default, so a reset has nothing to do."""
    catalog = _catalog({"table-default.owner": "data-eng"})
    rows = _by_key(resolve_table_properties(_table({"owner": "data-eng"}), catalog, CATALOGUE))

    row = rows["owner"]
    assert (row.custom, row.default_source, row.modified) == (True, "catalog", False)


def test_a_custom_key_off_its_catalog_default_is_modified_and_reset_writes_the_default():
    """A custom key away from the catalog's default is modified; its reset writes the catalog value back."""
    catalog = _catalog({"table-default.owner": "data-eng"})
    rows = _by_key(resolve_table_properties(_table({"owner": "kc"}), catalog, CATALOGUE))

    assert (rows["owner"].modified, rows["owner"].reset_value()) == (True, "data-eng")


@pytest.mark.parametrize(
    ("key", "catalog_properties", "written"),
    [
        ("write.parquet.compression-codec", {}, "zstd"),
        ("write.format.default", {"table-default.write.format.default": "orc"}, "orc"),
    ],
)
def test_an_unset_key_whose_default_does_not_apply_is_modified(
    key: str, catalog_properties: dict[str, str], written: str
):
    """Unset, a key a new table would hold falls back to Iceberg's own value, so it is modified; reset writes it."""
    rows = _by_key(resolve_table_properties(_table({}), _catalog(catalog_properties), CATALOGUE))

    row = rows[key]
    assert (row.current_value, row.modified, row.reset_value()) == (None, True, written)


def test_created_at_is_never_modified_and_has_no_default():
    """The catalog service's created-at is listed without a default or source, never modified, never resettable."""
    catalog = _catalog({"table-default.created-at": "ignored"})
    rows = _by_key(resolve_table_properties(_table({"created-at": "2026-11-14T00:00:00Z"}), catalog, CATALOGUE))

    row = rows["created-at"]
    assert (row.default_value, row.default_source, row.custom) == (None, None, False)
    assert (row.modified, row.resettable, row.set_by_catalog) == (False, False, True)
