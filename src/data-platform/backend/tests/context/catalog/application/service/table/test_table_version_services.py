"""Test listing a table's schema and partition spec versions and comparing any two, over the in-memory repo."""

from __future__ import annotations

import re

import pytest

from context.catalog.application.exceptions import NotFoundError
from context.catalog.application.port.inbound.table import (
    GetTablePartitionSpecComparisonUseCaseInput,
    GetTableSchemaComparisonUseCaseInput,
    ListTablePartitionSpecVersionsUseCaseInput,
    ListTableSchemaVersionsUseCaseInput,
)
from context.catalog.application.port.outbound.table import (
    PartitionField,
    PartitionSpec,
    PartitionTransform,
    PartitionTransformKind,
    Schema,
    SchemaField,
    SchemaFieldKind,
    SortOrder,
    Table,
    TableId,
)
from context.catalog.application.service.table import (
    GetTablePartitionSpecComparisonService,
    GetTableSchemaComparisonService,
    ListTablePartitionSpecVersionsService,
    ListTableSchemaVersionsService,
)
from tests.context.catalog.fakes.in_memory_tables_repo import InMemoryTablesRepo

TABLE_ID = TableId.of("sales", ("retail",), "orders")
DAY = PartitionTransform(kind=PartitionTransformKind.DAY)
HOUR = PartitionTransform(kind=PartitionTransformKind.HOUR)
BUCKET_16 = PartitionTransform(kind=PartitionTransformKind.BUCKET, argument=16)
MISSING = re.escape("table missing not found in namespace ['retail'] of catalog sales")


def _field(field_id: int, name: str, type_: str = "string", doc: str | None = None, *children: SchemaField):
    kind = SchemaFieldKind.STRUCT if children else SchemaFieldKind.PRIMITIVE
    return SchemaField(id=field_id, name=name, type=type_, required=False, doc=doc, kind=kind, children=children)


@pytest.fixture
def tables_repo() -> InMemoryTablesRepo:
    """Provide a repo holding sales.retail.orders with schemas 0 and 1 and partition specs 0 and 1.

    Schema 1 adds fields 4 to 8 (``address`` with two children, ``region`` and ``note``) and documents
    ``customer_id``; spec 1 adds ``bucket[16](customer_id)`` to spec 0's ``day(order_ts)``.
    """
    repo = InMemoryTablesRepo()
    schema_0 = Schema(
        schema_id=0,
        fields=(_field(1, "order_id", "long"), _field(2, "customer_id", "long"), _field(3, "order_ts", "timestamp")),
    )
    schema_1 = Schema(
        schema_id=1,
        fields=(
            _field(1, "order_id", "long"),
            _field(2, "customer_id", "long", "who bought"),
            _field(3, "order_ts", "timestamp"),
            _field(4, "address", "struct<city: string, zip: string>", None, _field(5, "city"), _field(6, "zip")),
            _field(7, "region"),
            _field(8, "note"),
        ),
    )
    day = PartitionField(source_id=3, field_id=1000, name="order_ts_day", transform=DAY)
    bucket = PartitionField(source_id=2, field_id=1001, name="customer_id_bucket", transform=BUCKET_16)
    repo.items[TABLE_ID.value] = Table(
        id=TABLE_ID,
        uuid="u-1",
        format_version=2,
        location="s3://w/retail/orders",
        current_snapshot_id=None,
        last_updated_ms=1,
        schemas=(schema_0, schema_1),
        current_schema_id=1,
        partition_specs=(PartitionSpec(spec_id=0, fields=(day,)), PartitionSpec(spec_id=1, fields=(day, bucket))),
        default_spec_id=1,
        sort_order=SortOrder.unsorted(),
    )
    return repo


def _schema_input(
    schema_id: int, base: int | None = None, name: str = "orders"
) -> GetTableSchemaComparisonUseCaseInput:
    return GetTableSchemaComparisonUseCaseInput(
        catalog="sales", namespace=("retail",), name=name, schema_id=schema_id, base_schema_id=base
    )


def _spec_input(
    spec_id: int, base: int | None = None, name: str = "orders"
) -> GetTablePartitionSpecComparisonUseCaseInput:
    return GetTablePartitionSpecComparisonUseCaseInput(
        catalog="sales", namespace=("retail",), name=name, spec_id=spec_id, base_spec_id=base
    )


def test_schema_versions_newest_first_with_counts(tables_repo):
    """Versions list newest id first, each with its column count and its changes against the previous one."""
    out = ListTableSchemaVersionsService(tables_repo).execute(
        ListTableSchemaVersionsUseCaseInput(catalog="sales", namespace=("retail",), name="orders")
    )

    assert out.current_schema_id == 1
    assert [(v.schema_id, v.previous_schema_id, v.current, v.column_count) for v in out.items] == [
        (1, 0, True, 6),
        (0, None, False, 3),
    ]
    assert out.items[0].changes == {
        "added": 5,
        "removed": 0,
        "renamed": 0,
        "type_changed": 0,
        "nullability_changed": 0,
        "doc_changed": 1,
    }
    assert out.items[1].changes is None


def test_schema_comparison_defaults_to_the_previous_version(tables_repo):
    """Without a base, a schema is compared with the version below it."""
    out = GetTableSchemaComparisonService(tables_repo).execute(_schema_input(1))

    assert (out.base_schema_id, out.schema_id) == (0, 1)
    by_id = {field.field_id: field for field in out.items}
    assert by_id[2].changes == ("doc_changed",)
    assert (by_id[2].doc, by_id[2].previous_doc) == ("who bought", None)
    assert by_id[5].path == ("address", "city")
    assert [by_id[i].changes for i in (4, 5, 6, 7, 8)] == [("added",)] * 5
    assert by_id[1].changes == ()


def test_schema_comparison_with_a_chosen_base(tables_repo):
    """A chosen base, even a newer one, is what the schema is set against."""
    out = GetTableSchemaComparisonService(tables_repo).execute(_schema_input(0, base=1))

    assert (out.base_schema_id, out.schema_id) == (1, 0)
    assert {field.field_id for field in out.items if field.changes == ("removed",)} == {4, 5, 6, 7, 8}
    removed = next(field for field in out.items if field.field_id == 5)
    assert (removed.path, removed.previous_path, removed.type) == (None, ("address", "city"), None)


def test_first_schema_has_no_base(tables_repo):
    """The first version has no earlier one: every field is unchanged."""
    out = GetTableSchemaComparisonService(tables_repo).execute(_schema_input(0))

    assert out.base_schema_id is None
    assert [field.field_id for field in out.items] == [1, 2, 3]
    assert all(field.changes == () for field in out.items)


def test_schema_compared_with_itself_is_all_unchanged(tables_repo):
    """A base equal to the schema is allowed and changes nothing."""
    out = GetTableSchemaComparisonService(tables_repo).execute(_schema_input(1, base=1))

    assert out.base_schema_id == 1
    assert all(field.changes == () for field in out.items)


def test_unknown_schema_or_base_is_not_found(tables_repo):
    """An unknown schema id, or an unknown base, is NotFoundError naming that id."""
    service = GetTableSchemaComparisonService(tables_repo)

    with pytest.raises(NotFoundError, match=r"^schema 9 not found in table orders$"):
        service.execute(_schema_input(9))
    with pytest.raises(NotFoundError, match=r"^schema 7 not found in table orders$"):
        service.execute(_schema_input(1, base=7))


def test_partition_spec_versions_mark_the_default(tables_repo):
    """Versions list newest id first, the default one marked, with their field counts and changes."""
    out = ListTablePartitionSpecVersionsService(tables_repo).execute(
        ListTablePartitionSpecVersionsUseCaseInput(catalog="sales", namespace=("retail",), name="orders")
    )

    assert out.default_spec_id == 1
    assert [(v.spec_id, v.previous_spec_id, v.default, v.field_count) for v in out.items] == [
        (1, 0, True, 2),
        (0, None, False, 1),
    ]
    assert out.items[0].changes == {"added": 1, "removed": 0, "renamed": 0, "transform_changed": 0}
    assert out.items[1].changes is None


def test_partition_spec_versions_walk_the_column_paths_once(tables_repo, monkeypatch):
    """The column paths are walked once per listing, not once per spec."""
    walks: list[int] = []
    column_paths = Table.column_paths

    def counted(table: Table) -> dict[int, tuple[str, ...]]:
        walks.append(1)
        return column_paths(table)

    monkeypatch.setattr(Table, "column_paths", counted)

    ListTablePartitionSpecVersionsService(tables_repo).execute(
        ListTablePartitionSpecVersionsUseCaseInput(catalog="sales", namespace=("retail",), name="orders")
    )

    assert len(walks) == 1


def test_partition_comparison_carries_transform_text_and_source_columns(tables_repo):
    """Each field carries its transform as Iceberg text and its source column id and path."""
    out = GetTablePartitionSpecComparisonService(tables_repo).execute(_spec_input(1))

    assert (out.base_spec_id, out.spec_id) == (0, 1)
    added = next(field for field in out.items if field.field_id == 1001)
    assert (added.transform, added.previous_transform, added.changes) == ("bucket[16]", None, ("added",))
    assert (added.source_id, added.source_path) == (2, ("customer_id",))
    assert (added.previous_source_id, added.previous_source_path) == (None, None)
    kept = next(field for field in out.items if field.field_id == 1000)
    assert (kept.transform, kept.previous_transform, kept.changes) == ("day", "day", ())
    assert (kept.source_path, kept.previous_source_path) == (("order_ts",), ("order_ts",))


def test_partition_field_on_a_column_no_schema_holds_has_its_id_and_no_path(tables_repo):
    """A source column missing from every schema reaches the output as its id with no path."""
    table = tables_repo.items[TABLE_ID.value]
    region = PartitionField(source_id=42, field_id=1002, name="region", transform=BUCKET_16)
    specs = (*table.partition_specs, PartitionSpec(spec_id=2, fields=(region,)))
    tables_repo.items[TABLE_ID.value] = table.model_copy(update={"partition_specs": specs})

    out = GetTablePartitionSpecComparisonService(tables_repo).execute(_spec_input(2, base=2))

    (field,) = out.items
    assert (field.source_id, field.source_path, field.previous_source_id, field.previous_source_path) == (
        42,
        None,
        42,
        None,
    )


def test_partition_comparison_with_a_chosen_base_and_the_first_spec(tables_repo):
    """A newer base shows the field as removed; the first spec has no base."""
    service = GetTablePartitionSpecComparisonService(tables_repo)

    reverse = service.execute(_spec_input(0, base=1))
    first = service.execute(_spec_input(0))

    removed = next(field for field in reverse.items if field.previous_field_id == 1001)
    assert (removed.changes, removed.transform, removed.previous_transform) == (("removed",), None, "bucket[16]")
    assert (removed.source_path, removed.previous_source_path) == (None, ("customer_id",))
    assert first.base_spec_id is None
    assert [field.changes for field in first.items] == [()]


def test_unknown_partition_spec_or_base_is_not_found(tables_repo):
    """An unknown spec id, or an unknown base, is NotFoundError naming that id."""
    service = GetTablePartitionSpecComparisonService(tables_repo)

    with pytest.raises(NotFoundError, match=r"^partition spec 4 not found in table orders$"):
        service.execute(_spec_input(4))
    with pytest.raises(NotFoundError, match=r"^partition spec 5 not found in table orders$"):
        service.execute(_spec_input(1, base=5))


def test_unknown_table_is_not_found(tables_repo):
    """All four services say so for a table the catalog does not have."""
    list_input = {"catalog": "sales", "namespace": ("retail",), "name": "missing"}

    with pytest.raises(NotFoundError, match=MISSING):
        ListTableSchemaVersionsService(tables_repo).execute(ListTableSchemaVersionsUseCaseInput(**list_input))
    with pytest.raises(NotFoundError, match=MISSING):
        GetTableSchemaComparisonService(tables_repo).execute(_schema_input(1, name="missing"))
    with pytest.raises(NotFoundError, match=MISSING):
        ListTablePartitionSpecVersionsService(tables_repo).execute(
            ListTablePartitionSpecVersionsUseCaseInput(**list_input)
        )
    with pytest.raises(NotFoundError, match=MISSING):
        GetTablePartitionSpecComparisonService(tables_repo).execute(_spec_input(1, name="missing"))


@pytest.fixture
def reused_ids_repo(tables_repo) -> InMemoryTablesRepo:
    """Provide orders with schemas 0, 1 and 2 where schema 1 is current, and specs 0 and 2 where spec 0 is the default.

    Iceberg reuses an existing id when a change produces a schema or spec it already has, so the
    current one need not be the highest, and ids need not be consecutive.
    """
    table = tables_repo.items[TABLE_ID.value]
    schema_2 = Schema(schema_id=2, fields=(*table.schemas[1].fields, _field(9, "channel")))
    day = PartitionField(source_id=3, field_id=1000, name="order_ts_day", transform=DAY)
    hour = PartitionField(source_id=3, field_id=1002, name="order_ts_hour", transform=HOUR)
    tables_repo.items[TABLE_ID.value] = table.model_copy(
        update={
            "schemas": (*table.schemas, schema_2),
            "current_schema_id": 1,
            "partition_specs": (PartitionSpec(spec_id=0, fields=(day,)), PartitionSpec(spec_id=2, fields=(hour,))),
            "default_spec_id": 0,
        }
    )
    return tables_repo


def test_current_schema_and_default_spec_follow_the_metadata_not_the_highest_id(reused_ids_repo):
    """Only schema 1 is current and only spec 0 is the default, though schema 2 and spec 2 are higher."""
    schemas = ListTableSchemaVersionsService(reused_ids_repo).execute(
        ListTableSchemaVersionsUseCaseInput(catalog="sales", namespace=("retail",), name="orders")
    )
    specs = ListTablePartitionSpecVersionsService(reused_ids_repo).execute(
        ListTablePartitionSpecVersionsUseCaseInput(catalog="sales", namespace=("retail",), name="orders")
    )

    assert schemas.current_schema_id == 1
    assert [(v.schema_id, v.current) for v in schemas.items] == [(2, False), (1, True), (0, False)]
    assert specs.default_spec_id == 0
    assert [(v.spec_id, v.previous_spec_id, v.default) for v in specs.items] == [(2, 0, False), (0, None, True)]


def test_default_base_is_the_next_lower_id_not_the_id_minus_one(reused_ids_repo):
    """Spec 2 is set against spec 0, the next lower id the table has, never against a missing spec 1."""
    out = GetTablePartitionSpecComparisonService(reused_ids_repo).execute(_spec_input(2))

    assert (out.base_spec_id, out.spec_id) == (0, 2)
    assert {(field.previous_transform, field.transform, field.changes) for field in out.items} == {
        ("day", "hour", ("transform_changed",))
    }
