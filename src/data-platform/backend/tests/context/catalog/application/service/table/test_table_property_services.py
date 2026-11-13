"""Test listing a table's properties against their defaults and resetting them, over the in-memory repos."""

from __future__ import annotations

import pytest

from context.catalog.application.exceptions import ConflictError, NotFoundError, ValidationError
from context.catalog.application.port.inbound.table import (
    ListTablePropertiesUseCaseInput,
    ListTablePropertiesUseCaseOutputItem,
    ResetTablePropertiesUseCaseInput,
)
from context.catalog.application.port.outbound.catalog import (
    Catalog,
    CatalogId,
    CatalogType,
    StorageConfig,
    StorageType,
)
from context.catalog.application.port.outbound.table import (
    PartitionSpec,
    Schema,
    SchemaField,
    SortOrder,
    Table,
    TableId,
)
from context.catalog.application.service.table import (
    ListTablePropertiesService,
    ResetTablePropertiesService,
)
from tests.context.catalog.fakes.in_memory_catalogs_repo import InMemoryCatalogsRepo
from tests.context.catalog.fakes.in_memory_tables_repo import InMemoryTablesRepo

TABLE_ID = TableId.of("sales", ("retail",), "orders")


@pytest.fixture
def tables() -> InMemoryTablesRepo:
    """Provide a tables repo holding sales.retail.orders, uuid u-1, format version 2."""
    repo = InMemoryTablesRepo()
    repo.items[TABLE_ID.value] = Table(
        id=TABLE_ID,
        uuid="u-1",
        format_version=2,
        location="s3://w/retail/orders",
        current_snapshot_id=None,
        last_updated_ms=1,
        current_schema=Schema(
            schema_id=0, fields=(SchemaField(id=1, name="id", type="long", required=True, doc=None),)
        ),
        partition_spec=PartitionSpec.unpartitioned(),
        sort_order=SortOrder.unsorted(),
        properties={
            "write.format.default": "orc",
            "write.parquet.compression-codec": "gzip",
            "commit.retry.num-retries": "4",
            "owner": "data-eng",
        },
    )
    return repo


def _catalogs(properties: dict[str, str] | None = None) -> InMemoryCatalogsRepo:
    repo = InMemoryCatalogsRepo()
    repo.items["sales"] = Catalog(
        id=CatalogId.of("sales"),
        type=CatalogType.INTERNAL,
        properties={"default-base-location": "s3://w", **(properties or {})},
        storage_config=StorageConfig(storage_type=StorageType.S3, allowed_locations=("s3://w",)),
    )
    return repo


def _list(tables: InMemoryTablesRepo, catalogs: InMemoryCatalogsRepo):
    return ListTablePropertiesService(tables, catalogs).execute(
        ListTablePropertiesUseCaseInput("sales", ["retail"], "orders")
    )


def _reset(tables: InMemoryTablesRepo, catalogs: InMemoryCatalogsRepo, keys: list[str], uuid: str = "u-1"):
    return ResetTablePropertiesService(tables, catalogs).execute(
        ResetTablePropertiesUseCaseInput("sales", ["retail"], "orders", expected_uuid=uuid, keys=keys)
    )


def _row(items: list, key: str):
    return next(item for item in items if item.key == key)


def test_list_returns_every_known_and_custom_property_with_its_default(tables: InMemoryTablesRepo):
    """The listing names the table's uuid and the Iceberg version, and resolves every row."""
    output = _list(tables, _catalogs())

    assert (output.uuid, output.iceberg_version) == ("u-1", "1.10.1")
    assert _row(output.items, "write.format.default") == ListTablePropertiesUseCaseOutputItem(
        key="write.format.default",
        current_value="orc",
        default_value="parquet",
        default_source="iceberg",
        modified=True,
        custom=False,
        resettable=True,
        description="File format of new data files.",
    )
    owner = _row(output.items, "owner")
    assert (owner.custom, owner.modified, owner.default_value, owner.default_source) == (True, True, None, None)
    assert _row(output.items, "format-version").current_value == "2"
    assert _row(output.items, "commit.retry.num-retries").modified is False


def test_list_shows_the_catalog_default_and_override(tables: InMemoryTablesRepo):
    """A catalog default and override are the defaults shown; an override is not resettable."""
    catalogs = _catalogs({"table-default.write.format.default": "orc", "table-override.owner": "platform"})

    items = _list(tables, catalogs).items

    assert _row(items, "write.format.default").default_source == "catalog"
    assert _row(items, "write.format.default").modified is False
    owner = _row(items, "owner")
    assert (owner.default_value, owner.default_source, owner.resettable) == ("platform", "catalog_override", False)


def test_list_unknown_table_is_not_found(tables: InMemoryTablesRepo):
    """A table that is not there is a NotFoundError."""
    with pytest.raises(NotFoundError):
        ListTablePropertiesService(tables, _catalogs()).execute(
            ListTablePropertiesUseCaseInput("sales", ["retail"], "missing")
        )


def test_list_unknown_catalog_is_not_found(tables: InMemoryTablesRepo):
    """The catalog's defaults are needed, so a catalog that is gone is a NotFoundError."""
    with pytest.raises(NotFoundError, match="catalog sales not found"):
        _list(tables, InMemoryCatalogsRepo())


def test_reset_removes_a_modified_key_and_returns_the_rows_as_saved(tables: InMemoryTablesRepo):
    """Reset removes the key through the property commit and answers with the refreshed rows."""
    output = _reset(tables, _catalogs(), ["write.format.default"])

    assert tables.property_commits == [({}, ["write.format.default"])]
    row = _row(output.items, "write.format.default")
    assert (row.current_value, row.modified) == (None, False)
    assert output.uuid == "u-1"


def test_reset_writes_the_default_a_new_table_holds(tables: InMemoryTablesRepo):
    """Parquet compression is written back as zstd; a catalog default is written back as the catalog's value."""
    catalogs = _catalogs({"table-default.write.format.default": "avro"})

    _reset(tables, catalogs, ["write.parquet.compression-codec", "write.format.default"])

    assert tables.property_commits == [
        ({"write.format.default": "avro", "write.parquet.compression-codec": "zstd"}, [])
    ]


def test_reset_deletes_a_custom_property(tables: InMemoryTablesRepo):
    """Deleting a custom property is the same reset: the key is removed."""
    output = _reset(tables, _catalogs(), ["owner"])

    assert tables.property_commits == [({}, ["owner"])]
    assert all(item.key != "owner" for item in output.items)


def test_reset_of_keys_already_at_default_commits_nothing(tables: InMemoryTablesRepo):
    """Nothing to change means no commit, and the answer is the current rows."""
    output = _reset(tables, _catalogs(), ["commit.retry.num-retries", "write.data.path"])

    assert tables.property_commits == []
    assert _row(output.items, "owner").current_value == "data-eng"


def test_reset_refuses_a_key_that_is_not_resettable(tables: InMemoryTablesRepo):
    """Format version cannot be reset; the refusal is a ValidationError and nothing is written."""
    with pytest.raises(ValidationError, match="format-version cannot be reset"):
        _reset(tables, _catalogs(), ["write.format.default", "format-version"])

    assert tables.property_commits == []


def test_reset_refuses_a_key_the_catalog_forces(tables: InMemoryTablesRepo):
    """A catalog override is not resettable."""
    with pytest.raises(ValidationError, match="the catalog forces its value"):
        _reset(tables, _catalogs({"table-override.owner": "platform"}), ["owner"])


def test_reset_of_a_replaced_table_is_a_conflict_asking_to_reload(tables: InMemoryTablesRepo):
    """A table that is no longer the one loaded is a ConflictError, and nothing is written."""
    with pytest.raises(ConflictError, match="changed since you loaded it, reload"):
        _reset(tables, _catalogs(), ["owner"], uuid="u-old")

    assert tables.property_commits == []


@pytest.mark.parametrize(("keys", "uuid"), [([], "u-1"), (["owner"], " ")])
def test_reset_needs_keys_and_the_loaded_uuid(tables: InMemoryTablesRepo, keys: list[str], uuid: str):
    """A reset names at least one key and the uuid of the table as it was loaded."""
    with pytest.raises(ValidationError):
        _reset(tables, _catalogs(), keys, uuid=uuid)


def test_reset_unknown_table_is_not_found(tables: InMemoryTablesRepo):
    """A table that is not there is a NotFoundError."""
    with pytest.raises(NotFoundError):
        ResetTablePropertiesService(tables, _catalogs()).execute(
            ResetTablePropertiesUseCaseInput("sales", ["retail"], "missing", expected_uuid="u-1", keys=["owner"])
        )
