"""Test that the tables repo sends the exact Iceberg REST requests and maps LoadTableResult replies."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from context.catalog.adapter.outbound.table.polaris import TablesPolarisRepo
from context.catalog.application.exceptions import (
    CatalogUnavailableError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from context.catalog.application.port.outbound.table import (
    NamespaceId,
    NullOrder,
    PartitionField,
    PartitionSpec,
    SchemaField,
    SortDirection,
    SortOrder,
    Table,
    TableId,
    TableSchema,
)
from tests.context.catalog.adapter.outbound.shared.polaris.polaris_stub import PolarisStub

FIXTURE = Path(__file__).parent / "fixtures" / "load_table_result_v2.json"
TABLES = "/api/catalog/v1/sales/namespaces/retail/tables"
ORDERS = f"{TABLES}/orders"
ORDERS_ID = TableId.of("sales", ("retail",), "orders")
UUID = "9c12d441-03fe-4693-9a96-a0705ddf69c1"


def _load_result() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text())


def _body(request: httpx.Request) -> Any:  # noqa: ANN401
    return json.loads(request.content)


def _error(status: int, message: str) -> httpx.Response:
    return httpx.Response(status, json={"error": {"message": message, "type": "X", "code": status}})


def _new_orders(partition_spec: PartitionSpec | None = None, location: str | None = None) -> Table:
    return Table.define(
        id=ORDERS_ID,
        schema=TableSchema(
            schema_id=0,
            fields=(
                SchemaField(id=1, name="order_id", type="long", required=True, doc="key"),
                SchemaField(id=2, name="order_ts", type="timestamptz", required=False, doc=None),
                SchemaField(id=3, name="tags", type="list<string>", required=False, doc=None),
            ),
        ),
        partition_spec=partition_spec or PartitionSpec.unpartitioned(),
        location=location,
        properties={"owner": "data-eng"},
    )


def test_load_maps_schema_partition_sort_snapshots_and_summary():
    """A real v2 LoadTableResult maps to the current schema, default spec and order, every snapshot and the summary."""
    stub = PolarisStub()
    stub.on("GET", ORDERS, httpx.Response(200, json=_load_result()))

    table = TablesPolarisRepo(stub.client()).get(ORDERS_ID)

    assert table is not None
    assert (table.uuid, table.format_version, table.location) == (UUID, 2, "s3://lakehouse/iceberg/retail/orders")
    assert (table.current_snapshot_id, table.last_updated_ms) == (3051729675574597004, 1762516800123)
    assert table.schema.schema_id == 1
    assert [(f.id, f.name, f.type, f.required, f.doc) for f in table.schema.fields] == [
        (1, "order_id", "long", True, "Primary key from MySQL"),
        (2, "customer_id", "long", False, None),
        (3, "order_ts", "timestamptz", False, None),
        (4, "amount", "decimal(10,2)", False, None),
        (5, "tags", "list<string>", False, None),
        (7, "shipping", "struct<city: required string>", False, None),
    ]
    assert table.partition_spec == PartitionSpec(
        spec_id=0, fields=(PartitionField(source_id=3, field_id=1000, name="order_ts_day", transform="day"),)
    )
    assert table.sort_order.order_id == 1
    (sort_field,) = table.sort_order.fields
    assert (sort_field.source_id, sort_field.transform) == (1, "identity")
    assert (sort_field.direction, sort_field.null_order) == (SortDirection.ASC, NullOrder.NULLS_FIRST)
    first, current = table.snapshots
    assert (first.snapshot_id, first.parent_id, first.operation) == (8333017788700497002, None, "append")
    assert (current.snapshot_id, current.parent_id) == (3051729675574597004, 8333017788700497002)
    assert (current.timestamp_ms, current.operation) == (1762516800123, "overwrite")
    assert current.summary["added-records"] == "60"
    assert "operation" not in current.summary
    assert table.properties["owner"] == "data-eng"
    assert (table.summary.total_records, table.summary.total_data_files, table.summary.total_files_size) == (
        150,
        2,
        5120,
    )


def test_load_table_without_snapshots_has_an_empty_summary():
    """A table with no snapshot has no current snapshot and every summary count is None."""
    body = _load_result()
    metadata = body["metadata"]
    metadata["snapshots"] = []
    metadata["current-snapshot-id"] = None
    metadata["sort-orders"] = [{"order-id": 0, "fields": []}]
    metadata["default-sort-order-id"] = 0
    stub = PolarisStub()
    stub.on("GET", ORDERS, httpx.Response(200, json=body))

    table = TablesPolarisRepo(stub.client()).get(ORDERS_ID)

    assert table is not None
    assert (table.current_snapshot_id, table.snapshots) == (None, [])
    assert table.sort_order == SortOrder.unsorted()
    assert (table.summary.total_records, table.summary.total_data_files, table.summary.total_files_size) == (
        None,
        None,
        None,
    )


def test_load_maps_map_types_and_optional_nested_elements():
    """A map type and an optional nested element render in the readable type syntax."""
    body = _load_result()
    body["metadata"]["schemas"][1]["fields"].append(
        {
            "id": 9,
            "name": "attrs",
            "required": False,
            "type": {
                "type": "map",
                "key-id": 10,
                "key": "string",
                "value-id": 11,
                "value": {"type": "list", "element-id": 12, "element": "int", "element-required": True},
                "value-required": False,
            },
        }
    )
    stub = PolarisStub()
    stub.on("GET", ORDERS, httpx.Response(200, json=body))

    table = TablesPolarisRepo(stub.client()).get(ORDERS_ID)

    assert table is not None
    assert table.schema.fields[-1].type == "map<string, list<required int>>"


def test_get_unknown_table_is_none():
    """Polaris's 404 means there is no such table."""
    stub = PolarisStub()
    stub.on("GET", ORDERS, _error(404, "Table does not exist: retail.orders"))

    assert TablesPolarisRepo(stub.client()).get(ORDERS_ID) is None


def test_table_path_encodes_namespace_parts_and_name():
    """A nested namespace is ``a%1Fb.c`` in the path and a name with a space is encoded."""
    stub = PolarisStub()
    stub.on("GET", "/api/catalog/v1/sales/namespaces/a%1Fb.c/tables/my%20t", httpx.Response(200, json=_load_result()))

    table = TablesPolarisRepo(stub.client()).get(TableId.of("sales", ("a", "b.c"), "my t"))

    assert table is not None
    assert table.id == TableId.of("sales", ("a", "b.c"), "my t")


def test_list_in_returns_the_ids_polaris_names():
    """Listing returns one id per identifier, in Polaris's order."""
    stub = PolarisStub()
    stub.on(
        "GET",
        TABLES,
        httpx.Response(
            200,
            json={
                "identifiers": [{"namespace": ["retail"], "name": "orders"}, {"namespace": ["retail"], "name": "items"}]
            },
        ),
    )

    found = TablesPolarisRepo(stub.client()).list_in(NamespaceId.of("sales", ("retail",)))

    assert found == [ORDERS_ID, TableId.of("sales", ("retail",), "items")]


def test_list_in_refuses_a_paged_listing_instead_of_truncating():
    """A non-null next-page-token is a loud CatalogUnavailableError, never a short list."""
    stub = PolarisStub()
    stub.on(
        "GET",
        TABLES,
        httpx.Response(
            200, json={"identifiers": [{"namespace": ["retail"], "name": "orders"}], "next-page-token": "t"}
        ),
    )

    with pytest.raises(CatalogUnavailableError, match="paged listing"):
        TablesPolarisRepo(stub.client()).list_in(NamespaceId.of("sales", ("retail",)))


def test_list_in_unknown_namespace_is_not_found():
    """Polaris's 404 for an unknown namespace passes through."""
    stub = PolarisStub()
    stub.on("GET", TABLES, _error(404, "Namespace does not exist: retail"))

    with pytest.raises(NotFoundError, match="Namespace does not exist"):
        TablesPolarisRepo(stub.client()).list_in(NamespaceId.of("sales", ("retail",)))


def test_create_table_sends_schema_and_partition_spec():
    """Create posts the name, the struct schema, the partition spec, the location and the properties."""
    stub = PolarisStub()
    stub.on("POST", TABLES, httpx.Response(200, json=_load_result()))
    spec = PartitionSpec(
        spec_id=0, fields=(PartitionField(source_id=2, field_id=1000, name="order_ts_day", transform="day"),)
    )

    saved = TablesPolarisRepo(stub.client()).create(_new_orders(spec, location="s3://lakehouse/custom/orders"))

    (request,) = stub.requests
    assert (request.method, request.url.path) == ("POST", TABLES)
    assert _body(request) == {
        "name": "orders",
        "schema": {
            "type": "struct",
            "schema-id": 0,
            "fields": [
                {"id": 1, "name": "order_id", "type": "long", "required": True, "doc": "key"},
                {"id": 2, "name": "order_ts", "type": "timestamptz", "required": False},
                {
                    "id": 3,
                    "name": "tags",
                    "type": {"type": "list", "element-id": 4, "element": "string", "element-required": False},
                    "required": False,
                },
            ],
        },
        "partition-spec": {
            "spec-id": 0,
            "fields": [{"source-id": 2, "field-id": 1000, "name": "order_ts_day", "transform": "day"}],
        },
        "location": "s3://lakehouse/custom/orders",
        "properties": {"owner": "data-eng"},
    }
    assert saved.uuid == UUID
    assert saved.id == ORDERS_ID


def test_create_table_without_location_or_partitions_omits_both():
    """No location lets Polaris pick one, and an unpartitioned table sends no partition spec."""
    stub = PolarisStub()
    stub.on("POST", TABLES, httpx.Response(200, json=_load_result()))

    TablesPolarisRepo(stub.client()).create(_new_orders())

    body = _body(stub.requests[0])
    assert "location" not in body
    assert "partition-spec" not in body


def test_create_table_with_malformed_type_is_a_validation_error():
    """A type the readable syntax does not parse is refused before anything is sent."""
    stub = PolarisStub()
    table = Table.define(
        id=ORDERS_ID,
        schema=TableSchema(schema_id=0, fields=(SchemaField(1, "bad", "list<string", True, None),)),
        partition_spec=PartitionSpec.unpartitioned(),
        location=None,
        properties={},
    )

    with pytest.raises(ValidationError, match="list<string"):
        TablesPolarisRepo(stub.client()).create(table)
    assert stub.requests == []


def test_create_existing_table_is_a_conflict():
    """Polaris's 409 is a ConflictError carrying its message."""
    stub = PolarisStub()
    stub.on("POST", TABLES, _error(409, "Table already exists: retail.orders"))

    with pytest.raises(ConflictError, match="already exists"):
        TablesPolarisRepo(stub.client()).create(_new_orders())


def test_drop_table_never_purges():
    """Delete sends DELETE with purgeRequested=false, always."""
    stub = PolarisStub()
    stub.on("DELETE", ORDERS, httpx.Response(204))

    TablesPolarisRepo(stub.client()).delete(ORDERS_ID)

    (request,) = stub.requests
    assert (request.method, request.url.path) == ("DELETE", ORDERS)
    assert request.url.params["purgeRequested"] == "false"


def test_rename_sends_source_and_destination():
    """Rename posts the source and destination identifiers to the catalog's /tables/rename."""
    stub = PolarisStub()
    stub.on("POST", "/api/catalog/v1/sales/tables/rename", httpx.Response(204))

    TablesPolarisRepo(stub.client()).rename(ORDERS_ID, TableId.of("sales", ("archive", "a.b"), "orders_2025"))

    (request,) = stub.requests
    assert (request.method, request.url.path) == ("POST", "/api/catalog/v1/sales/tables/rename")
    assert _body(request) == {
        "source": {"namespace": ["retail"], "name": "orders"},
        "destination": {"namespace": ["archive", "a.b"], "name": "orders_2025"},
    }


def test_rename_onto_an_existing_table_is_a_conflict():
    """Polaris's 409 for a taken destination passes through."""
    stub = PolarisStub()
    stub.on("POST", "/api/catalog/v1/sales/tables/rename", _error(409, "Table already exists: retail.items"))

    with pytest.raises(ConflictError, match="already exists"):
        TablesPolarisRepo(stub.client()).rename(ORDERS_ID, TableId.of("sales", ("retail",), "items"))


def test_update_properties_sends_assert_table_uuid():
    """The commit asserts the loaded uuid, sets then removes properties, and maps the returned metadata."""
    stub = PolarisStub()
    commit_reply = _load_result()
    commit_reply.pop("config")
    stub.on("POST", ORDERS, httpx.Response(200, json=commit_reply))

    saved = TablesPolarisRepo(stub.client()).update_properties(ORDERS_ID, UUID, {"tier": "gold"}, ["stale"])

    (request,) = stub.requests
    assert (request.method, request.url.path) == ("POST", ORDERS)
    assert _body(request) == {
        "requirements": [{"type": "assert-table-uuid", "uuid": UUID}],
        "updates": [
            {"action": "set-properties", "updates": {"tier": "gold"}},
            {"action": "remove-properties", "removals": ["stale"]},
        ],
    }
    assert saved.uuid == UUID


def test_update_properties_leaves_out_an_empty_change():
    """Only the non-empty change is sent; the requirement is always there."""
    stub = PolarisStub()
    stub.on("POST", ORDERS, httpx.Response(200, json=_load_result()))

    TablesPolarisRepo(stub.client()).update_properties(ORDERS_ID, UUID, {}, ["stale"])

    assert _body(stub.requests[0])["updates"] == [{"action": "remove-properties", "removals": ["stale"]}]


def test_update_properties_failed_requirement_is_a_conflict():
    """Polaris answers 409 when the uuid requirement fails; the repo raises ConflictError."""
    stub = PolarisStub()
    stub.on("POST", ORDERS, _error(409, "Requirement failed: UUID does not match"))

    with pytest.raises(ConflictError):
        TablesPolarisRepo(stub.client()).update_properties(ORDERS_ID, "other-uuid", {"k": "v"}, [])


def test_list_all_walks_every_catalog_namespace_and_table():
    """list_all lists catalogs, walks namespaces level by level, lists their tables and loads each."""
    stub = PolarisStub()
    stub.on("GET", "/api/management/v1/catalogs", httpx.Response(200, json={"catalogs": [{"name": "sales"}]}))
    stub.on(
        "GET",
        "/api/catalog/v1/sales/namespaces",
        httpx.Response(200, json={"namespaces": [["retail"]]}),
        httpx.Response(200, json={"namespaces": []}),
    )
    stub.on("GET", TABLES, httpx.Response(200, json={"identifiers": [{"namespace": ["retail"], "name": "orders"}]}))
    stub.on("GET", ORDERS, httpx.Response(200, json=_load_result()))

    found = TablesPolarisRepo(stub.client()).list_all()

    assert [t.id for t in found] == [ORDERS_ID]
