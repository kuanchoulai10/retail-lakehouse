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
    Schema,
    SchemaField,
    SortDirection,
    SortOrder,
    Table,
    TableId,
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
        schema=Schema(
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
    assert table.current_schema.schema_id == 1
    assert [(f.id, f.name, f.type, f.required, f.doc) for f in table.current_schema.fields] == [
        (1, "order_id", "long", True, "Primary key from MySQL"),
        (2, "customer_id", "long", False, None),
        (3, "order_ts", "timestamptz", False, None),
        (4, "amount", "decimal(10,2)", False, None),
        (5, "tags", "list<string>", False, None),
        (7, "shipping", "struct<city: required string>", False, None),
    ]
    assert table.partition_spec == PartitionSpec(
        spec_id=1,
        fields=(
            PartitionField(source_id=3, field_id=1000, name="order_ts_day", transform="day"),
            PartitionField(source_id=2, field_id=1001, name="customer_id_bucket", transform="bucket[16]"),
        ),
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
    assert table.current_schema.fields[-1].type == "map<string, list<required int>>"


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
        schema=Schema(
            schema_id=0, fields=(SchemaField(id=1, name="bad", type="list<string", required=True, doc=None),)
        ),
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


def _metadata_without(*keys: str) -> dict[str, Any]:
    body = _load_result()
    for key in keys:
        body["metadata"].pop(key)
    return body


def _malformed_variants() -> dict[str, httpx.Response]:
    unknown_direction = _load_result()
    unknown_direction["metadata"]["sort-orders"][1]["fields"][0]["direction"] = "sideways"
    current_schema_missing = _load_result()
    current_schema_missing["metadata"]["current-schema-id"] = 7
    default_spec_missing = _load_result()
    default_spec_missing["metadata"]["default-spec-id"] = 7
    default_order_missing = _load_result()
    default_order_missing["metadata"]["default-sort-order-id"] = 7
    return {
        "missing table-uuid": httpx.Response(200, json=_metadata_without("table-uuid")),
        "missing location": httpx.Response(200, json=_metadata_without("location")),
        "unknown sort direction": httpx.Response(200, json=unknown_direction),
        "no metadata": httpx.Response(200, json={"metadata-location": "s3://x"}),
        "not json": httpx.Response(200, text="<html>oops</html>"),
        "metadata is a list": httpx.Response(200, json={"metadata": []}),
        "current schema id matches no schema": httpx.Response(200, json=current_schema_missing),
        "default spec id matches no spec": httpx.Response(200, json=default_spec_missing),
        "default sort order id matches no order": httpx.Response(200, json=default_order_missing),
    }


@pytest.mark.parametrize("variant", sorted(_malformed_variants()))
def test_malformed_load_table_result_is_unavailable_not_a_crash(variant: str):
    """Metadata this backend cannot read is a CatalogUnavailableError naming the table, never a bare error."""
    stub = PolarisStub()
    stub.on("GET", ORDERS, _malformed_variants()[variant])

    with pytest.raises(CatalogUnavailableError, match="table orders in a form this backend cannot read"):
        TablesPolarisRepo(stub.client()).get(ORDERS_ID)


@pytest.mark.parametrize("method", ["create", "update_properties"])
def test_malformed_write_reply_is_unavailable(method: str):
    """A create or commit reply without readable metadata is a CatalogUnavailableError too."""
    stub = PolarisStub()
    stub.on("POST", TABLES, httpx.Response(200, json={"metadata": {}}))
    stub.on("POST", ORDERS, httpx.Response(200, json={"metadata": {}}))
    repo = TablesPolarisRepo(stub.client())

    with pytest.raises(CatalogUnavailableError, match="cannot read"):
        if method == "create":
            repo.create(_new_orders())
        else:
            repo.update_properties(ORDERS_ID, UUID, {"k": "v"}, [])


@pytest.mark.parametrize(
    "body",
    [{"identifiers": [{"name": "orders"}]}, {"identifiers": [{"namespace": "retail"}]}, ["orders"]],
)
def test_malformed_table_listing_is_unavailable(body: object):
    """An identifier without a namespace or name, or a reply that is not an object, is unavailable."""
    stub = PolarisStub()
    stub.on("GET", TABLES, httpx.Response(200, json=body))

    with pytest.raises(CatalogUnavailableError, match="cannot read"):
        TablesPolarisRepo(stub.client()).list_in(NamespaceId.of("sales", ("retail",)))


def test_v1_metadata_without_schemas_or_specs_uses_the_single_schema_and_spec():
    """Without ``schemas`` the v1 ``schema`` is current; without ``default-spec-id`` the v1 ``partition-spec`` is."""
    body = _load_result()
    metadata = body["metadata"]
    metadata["format-version"] = 1
    metadata["schema"] = metadata.pop("schemas")[0]
    metadata.pop("current-schema-id")
    metadata.pop("partition-specs")
    metadata.pop("default-spec-id")
    metadata["partition-spec"] = [{"name": "order_ts_day", "transform": "day", "source-id": 3, "field-id": 1000}]
    metadata.pop("sort-orders")
    metadata.pop("default-sort-order-id")
    stub = PolarisStub()
    stub.on("GET", ORDERS, httpx.Response(200, json=body))

    table = TablesPolarisRepo(stub.client()).get(ORDERS_ID)

    assert table is not None
    assert [f.name for f in table.current_schema.fields] == ["order_id", "customer_id", "order_ts"]
    assert table.partition_spec == PartitionSpec(
        spec_id=0, fields=(PartitionField(source_id=3, field_id=1000, name="order_ts_day", transform="day"),)
    )
    assert table.sort_order == SortOrder.unsorted()


def _snapshot(metadata: dict[str, Any]) -> dict[str, Any]:
    return metadata["snapshots"][1]


def _schema_field(metadata: dict[str, Any]) -> dict[str, Any]:
    return metadata["schemas"][1]["fields"][0]


def _partition_field(metadata: dict[str, Any]) -> dict[str, Any]:
    return metadata["partition-specs"][1]["fields"][0]


def _sort_field(metadata: dict[str, Any]) -> dict[str, Any]:
    return metadata["sort-orders"][1]["fields"][0]


ILL_TYPED = {
    "table-uuid is a number": lambda m: m.update({"table-uuid": 7}),
    "format-version is a bool": lambda m: m.update({"format-version": True}),
    "format-version is text": lambda m: m.update({"format-version": "2"}),
    "location is null": lambda m: m.update({"location": None}),
    "location is a number": lambda m: m.update({"location": 3}),
    "current-snapshot-id is text": lambda m: m.update({"current-snapshot-id": "3051729675574597004"}),
    "current-snapshot-id is a bool": lambda m: m.update({"current-snapshot-id": True}),
    "last-updated-ms is a float": lambda m: m.update({"last-updated-ms": 1762516800123.0}),
    "last-updated-ms is text": lambda m: m.update({"last-updated-ms": "1762516800123"}),
    "properties is a list of pairs": lambda m: m.update({"properties": [["owner", "data-eng"]]}),
    "properties is an empty list": lambda m: m.update({"properties": []}),
    "property value is a number": lambda m: m.update({"properties": {"owner": 1}}),
    "snapshots is an object": lambda m: m.update({"snapshots": {}}),
    "snapshot-id is text": lambda m: _snapshot(m).update({"snapshot-id": "3051729675574597004"}),
    "parent-snapshot-id is text": lambda m: _snapshot(m).update({"parent-snapshot-id": "8333017788700497002"}),
    "timestamp-ms is a bool": lambda m: _snapshot(m).update({"timestamp-ms": True}),
    "summary is a list of pairs": lambda m: _snapshot(m).update({"summary": [["operation", "append"]]}),
    "summary value is a number": lambda m: _snapshot(m).update(
        {"summary": {"operation": "append", "added-records": 60}}
    ),
    "operation is a number": lambda m: _snapshot(m).update({"summary": {"operation": 1}}),
    "current-schema-id is a bool": lambda m: m.update({"current-schema-id": True}),
    "schema-id is text": lambda m: m["schemas"][1].update({"schema-id": "1"}),
    "schema field id is text": lambda m: _schema_field(m).update({"id": "1"}),
    "schema field name is a number": lambda m: _schema_field(m).update({"name": 1}),
    "schema field required is text": lambda m: _schema_field(m).update({"required": "yes"}),
    "default-spec-id is a bool": lambda m: m.update({"default-spec-id": True}),
    "partition source-id is text": lambda m: _partition_field(m).update({"source-id": "3"}),
    "partition field-id is a float": lambda m: _partition_field(m).update({"field-id": 1000.0}),
    "partition name is a number": lambda m: _partition_field(m).update({"name": 5}),
    "partition transform is null": lambda m: _partition_field(m).update({"transform": None}),
    "default-sort-order-id is a bool": lambda m: m.update({"default-sort-order-id": True}),
    "sort source-id is text": lambda m: _sort_field(m).update({"source-id": "1"}),
    "sort transform is a number": lambda m: _sort_field(m).update({"transform": 1}),
}


@pytest.mark.parametrize("change", ILL_TYPED.values(), ids=ILL_TYPED.keys())
def test_ill_typed_value_from_polaris_is_unavailable(change: Any):  # noqa: ANN401
    """A value of the wrong type is refused, never coerced into the table (a bool is not an integer)."""
    body = _load_result()
    change(body["metadata"])
    stub = PolarisStub()
    stub.on("GET", ORDERS, httpx.Response(200, json=body))

    with pytest.raises(CatalogUnavailableError, match="table orders in a form this backend cannot read"):
        TablesPolarisRepo(stub.client()).get(ORDERS_ID)


def test_absent_optional_values_from_polaris_keep_their_defaults():
    """No properties, snapshots, summary, parent or required flag, and -1 for no snapshot, read as before."""
    body = _load_result()
    metadata = body["metadata"]
    metadata.pop("properties")
    metadata["current-snapshot-id"] = -1
    metadata["snapshots"] = None
    _schema_field(metadata).pop("required")
    stub = PolarisStub()
    stub.on("GET", ORDERS, httpx.Response(200, json=body))

    table = TablesPolarisRepo(stub.client()).get(ORDERS_ID)

    assert table is not None
    assert (table.properties, table.snapshots, table.current_snapshot_id) == ({}, [], None)
    assert table.current_schema.fields[0].required is False


def test_a_loaded_table_holds_real_tuples_and_enums():
    """The mapper hands the strict domain tuples and enums, so every field has its declared type."""
    stub = PolarisStub()
    stub.on("GET", ORDERS, httpx.Response(200, json=_load_result()))

    table = TablesPolarisRepo(stub.client()).get(ORDERS_ID)

    assert table is not None
    assert type(table.partition_spec.fields) is tuple
    assert type(table.sort_order.fields) is tuple
    assert type(table.sort_order.fields[0].direction) is SortDirection
    assert type(table.sort_order.fields[0].null_order) is NullOrder
    assert type(table.snapshots) is list


CREATE_REQUEST_BYTES = (
    b'{"name":"orders","schema":{"type":"struct","schema-id":0,"fields":[{"id":1,"name":"order_id","type":"long",'
    b'"required":true,"doc":"key"},{"id":2,"name":"order_ts","type":"timestamptz","required":false},{"id":3,'
    b'"name":"tags","type":{"type":"list","element-id":4,"element":"string","element-required":false},'
    b'"required":false}]},"partition-spec":{"spec-id":0,"fields":[{"source-id":2,"field-id":1000,'
    b'"name":"order_ts_day","transform":"day"}]},"location":"s3://lakehouse/custom/orders",'
    b'"properties":{"owner":"data-eng"}}'
)


def test_create_request_bytes_are_unchanged():
    """The create body is byte for byte what it was before the domain moved to Pydantic."""
    stub = PolarisStub()
    stub.on("POST", TABLES, httpx.Response(200, json=_load_result()))
    spec = PartitionSpec(
        spec_id=0, fields=(PartitionField(source_id=2, field_id=1000, name="order_ts_day", transform="day"),)
    )

    TablesPolarisRepo(stub.client()).create(_new_orders(spec, location="s3://lakehouse/custom/orders"))

    assert stub.requests[0].content == CREATE_REQUEST_BYTES


def test_update_and_rename_request_bytes_are_unchanged():
    """The commit and rename bodies are byte for byte what they were before the domain moved to Pydantic."""
    stub = PolarisStub()
    stub.on("POST", ORDERS, httpx.Response(200, json=_load_result()))
    stub.on("POST", "/api/catalog/v1/sales/tables/rename", httpx.Response(204))
    repo = TablesPolarisRepo(stub.client())

    repo.update_properties(ORDERS_ID, "u-1", {"tier": "gold"}, ["stale"])
    repo.rename(ORDERS_ID, TableId.of("sales", ("archive", "a.b"), "orders_2025"))

    assert [request.content for request in stub.requests] == [
        b'{"requirements":[{"type":"assert-table-uuid","uuid":"u-1"}],"updates":[{"action":"set-properties",'
        b'"updates":{"tier":"gold"}},{"action":"remove-properties","removals":["stale"]}]}',
        b'{"source":{"namespace":["retail"],"name":"orders"},"destination":{"namespace":["archive","a.b"],'
        b'"name":"orders_2025"}}',
    ]
