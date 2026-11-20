"""Test the table routes."""

from __future__ import annotations

from typing import Any

from context.catalog.application.exceptions import ConflictError, NotFoundError, ValidationError
from context.catalog.application.port.inbound.table import (
    CreateTableUseCaseInput,
    CreateTableUseCaseOutput,
    DeleteTableUseCaseInput,
    DeleteTableUseCaseOutput,
    GetTableUseCaseInput,
    GetTableUseCaseOutput,
    ListTablePropertiesUseCaseInput,
    ListTablePropertiesUseCaseOutput,
    ListTablesUseCaseInput,
    ListTablesUseCaseOutput,
    RenameTableUseCaseInput,
    RenameTableUseCaseOutput,
    ResetTablePropertiesUseCaseInput,
    ResetTablePropertiesUseCaseOutput,
    UpdateTablePropertiesUseCaseInput,
    UpdateTablePropertiesUseCaseOutput,
)
from tests.context.catalog.adapter.inbound.web.web_test_support import StubUseCase, build_client

BASE = "/v1/catalogs/sales/namespaces/retail/tables"


def _fields() -> dict[str, Any]:
    return {
        "catalog": "sales",
        "namespace": ["retail"],
        "name": "orders",
        "uuid": "u-1",
        "format_version": 2,
        "location": "s3://w/retail/orders",
        "current_snapshot_id": 2,
        "last_updated_ms": 20,
        "schema": {
            "schema_id": 0,
            "fields": [{"id": 1, "name": "order_id", "type": "long", "required": True, "doc": None}],
        },
        "partition_spec": {
            "spec_id": 0,
            "fields": [{"source_id": 1, "field_id": 1000, "name": "order_id", "transform": "identity"}],
        },
        "sort_order": {
            "order_id": 1,
            "fields": [{"source_id": 1, "transform": "identity", "direction": "asc", "null_order": "nulls-first"}],
        },
        "snapshots": [
            {"id": 2, "parent_id": None, "timestamp_ms": 20, "schema_id": 0, "operation": "append", "summary": {}}
        ],
        "properties": {"owner": "data-eng"},
        "summary": {"total_records": 9, "total_data_files": 3, "total_files_size": 300},
    }


def _port(body: dict[str, Any]) -> dict[str, Any]:
    """Turn a REST-shaped table body into the output fields: tuples, and ``table_schema`` for ``schema``."""
    fields = {("table_schema" if key == "schema" else key): value for key, value in body.items()}
    fields["namespace"] = tuple(fields["namespace"])
    fields["snapshots"] = tuple(fields["snapshots"])
    return fields


def test_get_table_returns_every_panel_field():
    """Get returns the table with schema, spec, order, snapshots, properties and summary."""
    stub = StubUseCase(GetTableUseCaseOutput(**_port(_fields())))

    response = build_client(get_table=stub).get(f"{BASE}/orders")

    assert response.status_code == 200
    expected = _fields()
    expected["current_snapshot_id"] = "2"
    expected["snapshots"][0]["id"] = "2"
    assert response.json() == expected
    assert stub.requests == [GetTableUseCaseInput(catalog="sales", namespace=("retail",), name="orders")]


def test_get_table_shows_the_schema_id_of_each_snapshot():
    """Each snapshot carries the id of the schema it was written with, or null when the table does not record it."""
    fields = _fields()
    fields["snapshots"] = (
        *fields["snapshots"],
        {"id": 3, "parent_id": 2, "timestamp_ms": 30, "schema_id": None, "operation": "append", "summary": {}},
    )

    body = build_client(get_table=StubUseCase(GetTableUseCaseOutput(**_port(fields)))).get(f"{BASE}/orders").json()

    assert [s["schema_id"] for s in body["snapshots"]] == [0, None]


def test_snapshot_ids_above_two_to_the_53_are_exact_strings():
    """Snapshot ids are 64-bit; JSON carries them as text so a browser cannot round them (Ruling R9)."""
    fields = _fields()
    fields["current_snapshot_id"] = 3051729675574597004
    fields["snapshots"] = [
        {
            "id": 3051729675574597004,
            "parent_id": 8333017788700497002,
            "timestamp_ms": 20,
            "schema_id": 1,
            "operation": "overwrite",
            "summary": {},
        },
        {
            "id": 8333017788700497002,
            "parent_id": None,
            "timestamp_ms": 10,
            "schema_id": None,
            "operation": "append",
            "summary": {},
        },
    ]

    response = build_client(get_table=StubUseCase(GetTableUseCaseOutput(**_port(fields)))).get(f"{BASE}/orders")

    body = response.json()
    assert body["current_snapshot_id"] == "3051729675574597004"
    assert [(s["id"], s["parent_id"]) for s in body["snapshots"]] == [
        ("3051729675574597004", "8333017788700497002"),
        ("8333017788700497002", None),
    ]


def test_table_without_a_current_snapshot_has_a_null_id():
    """No current snapshot is null, not the string "None"."""
    fields = _fields()
    fields["current_snapshot_id"] = None

    response = build_client(get_table=StubUseCase(GetTableUseCaseOutput(**_port(fields)))).get(f"{BASE}/orders")

    assert response.json()["current_snapshot_id"] is None


def test_get_unknown_table_returns_404():
    """A missing table is a 404 with the message."""
    client = build_client(get_table=StubUseCase(error=NotFoundError("table orders not found in sales.retail")))

    response = client.get(f"{BASE}/orders")

    assert (response.status_code, response.json()) == (404, {"detail": "table orders not found in sales.retail"})


def test_table_route_splits_the_namespace_on_the_unit_separator():
    """``a%1Fb.c`` in the path is the parts a and b.c."""
    stub = StubUseCase(GetTableUseCaseOutput(**_port(_fields())))

    build_client(get_table=stub).get("/v1/catalogs/sales/namespaces/a%1Fb.c/tables/orders")

    assert stub.requests == [GetTableUseCaseInput(catalog="sales", namespace=("a", "b.c"), name="orders")]


def test_list_tables():
    """Listing returns the identifiers."""
    stub = StubUseCase(
        ListTablesUseCaseOutput(
            items=(ListTablesUseCaseOutput.Table(catalog="sales", namespace=("retail",), name="orders"),)
        )
    )

    response = build_client(list_tables=stub).get(BASE)

    assert response.json() == [{"catalog": "sales", "namespace": ["retail"], "name": "orders"}]
    assert stub.requests == [ListTablesUseCaseInput(catalog="sales", namespace=("retail",))]


def test_create_table_returns_201_and_passes_the_form():
    """Create passes name, schema fields, partition fields, location and properties."""
    stub = StubUseCase(CreateTableUseCaseOutput(**_port(_fields())))

    response = build_client(create_table=stub).post(
        BASE,
        json={
            "name": "orders",
            "schema_fields": [{"name": "order_id", "type": "long", "required": True, "doc": "key"}],
            "partition_fields": [{"source_column": "order_id", "transform": "bucket[16]"}],
            "location": "s3://w/custom",
            "properties": {"owner": "data-eng"},
        },
    )

    assert response.status_code == 201
    assert response.json()["uuid"] == "u-1"
    assert stub.requests == [
        CreateTableUseCaseInput(
            catalog="sales",
            namespace=("retail",),
            name="orders",
            schema_fields=(
                CreateTableUseCaseInput.SchemaField(name="order_id", type="long", required=True, doc="key"),
            ),
            partition_fields=(
                CreateTableUseCaseInput.PartitionField(source_column="order_id", transform="bucket[16]"),
            ),
            location="s3://w/custom",
            properties={"owner": "data-eng"},
        )
    ]


def test_create_table_rejects_unknown_fields():
    """A body field the form does not have is refused."""
    stub = StubUseCase()

    response = build_client(create_table=stub).post(
        BASE, json={"name": "t", "schema_fields": [{"name": "a", "type": "int"}], "stage_create": True}
    )

    assert response.status_code == 422
    assert stub.requests == []


def test_delete_table_returns_204():
    """Delete returns 204 with no body."""
    stub = StubUseCase(DeleteTableUseCaseOutput())

    response = build_client(delete_table=stub).delete(f"{BASE}/orders")

    assert response.status_code == 204
    assert stub.requests == [DeleteTableUseCaseInput(catalog="sales", namespace=("retail",), name="orders")]


def test_rename_table_returns_the_new_identity():
    """Rename passes the target and returns where the table now is."""
    stub = StubUseCase(RenameTableUseCaseOutput(catalog="sales", namespace=("archive",), name="orders_old"))

    response = build_client(rename_table=stub).post(
        f"{BASE}/orders/rename", json={"target_namespace": ["archive"], "target_name": "orders_old"}
    )

    assert response.status_code == 200
    assert response.json() == {"catalog": "sales", "namespace": ["archive"], "name": "orders_old"}
    assert stub.requests == [
        RenameTableUseCaseInput(
            catalog="sales",
            namespace=("retail",),
            name="orders",
            target_namespace=("archive",),
            target_name="orders_old",
        )
    ]


def test_update_table_properties_passes_the_loaded_uuid():
    """PUT /properties passes the expected uuid, updates and removals."""
    stub = StubUseCase(UpdateTablePropertiesUseCaseOutput(**_port(_fields())))

    response = build_client(update_table_properties=stub).put(
        f"{BASE}/orders/properties", json={"expected_uuid": "u-1", "updates": {"tier": "gold"}, "removals": ["x"]}
    )

    assert response.status_code == 200
    assert stub.requests == [
        UpdateTablePropertiesUseCaseInput(
            catalog="sales",
            namespace=("retail",),
            name="orders",
            expected_uuid="u-1",
            updates={"tier": "gold"},
            removals=("x",),
        )
    ]


def test_update_table_properties_conflict_is_409_with_reload_message():
    """A table changed since it was loaded is a 409 telling the user to reload."""
    error = ConflictError("table orders changed since you loaded it, reload")
    client = build_client(update_table_properties=StubUseCase(error=error))

    response = client.put(f"{BASE}/orders/properties", json={"expected_uuid": "u-1"})

    assert (response.status_code, response.json()) == (
        409,
        {"detail": "table orders changed since you loaded it, reload"},
    )


_PROPERTY: dict[str, Any] = {
    "key": "write.format.default",
    "current_value": "orc",
    "default_value": "parquet",
    "default_source": "iceberg",
    "modified": True,
    "custom": False,
    "resettable": True,
    "description": "File format of new data files.",
}
_CUSTOM: dict[str, Any] = {
    "key": "owner",
    "current_value": "data-eng",
    "default_value": None,
    "default_source": None,
    "modified": True,
    "custom": True,
    "resettable": True,
    "description": None,
}


def test_list_table_properties_returns_every_row_with_its_default():
    """GET /properties answers the uuid, the Iceberg version and each property next to its default."""
    stub = StubUseCase(
        ListTablePropertiesUseCaseOutput(
            uuid="u-1",
            iceberg_version="1.10.1",
            items=(
                ListTablePropertiesUseCaseOutput.Property(**_PROPERTY),
                ListTablePropertiesUseCaseOutput.Property(**_CUSTOM),
            ),
        )
    )

    response = build_client(list_table_properties=stub).get(f"{BASE}/orders/properties")

    assert response.status_code == 200
    assert response.json() == {"uuid": "u-1", "iceberg_version": "1.10.1", "properties": [_PROPERTY, _CUSTOM]}
    assert stub.requests == [ListTablePropertiesUseCaseInput(catalog="sales", namespace=("retail",), name="orders")]


def test_list_table_properties_of_unknown_table_is_404():
    """A missing table is a 404 with the message."""
    client = build_client(list_table_properties=StubUseCase(error=NotFoundError("table orders not found")))

    response = client.get(f"{BASE}/orders/properties")

    assert (response.status_code, response.json()) == (404, {"detail": "table orders not found"})


def test_reset_table_properties_passes_the_keys_and_the_loaded_uuid():
    """POST /properties/reset passes the expected uuid and keys, and answers the rows as saved."""
    stub = StubUseCase(
        ResetTablePropertiesUseCaseOutput(
            uuid="u-1", iceberg_version="1.10.1", items=(ResetTablePropertiesUseCaseOutput.Property(**_CUSTOM),)
        )
    )

    response = build_client(reset_table_properties=stub).post(
        f"{BASE}/orders/properties/reset", json={"expected_uuid": "u-1", "keys": ["write.format.default"]}
    )

    assert response.status_code == 200
    assert response.json() == {"uuid": "u-1", "iceberg_version": "1.10.1", "properties": [_CUSTOM]}
    assert stub.requests == [
        ResetTablePropertiesUseCaseInput(
            catalog="sales", namespace=("retail",), name="orders", expected_uuid="u-1", keys=("write.format.default",)
        )
    ]


def test_reset_of_a_property_that_is_not_resettable_is_422():
    """A refused reset answers 422 with the reason."""
    error = ValidationError("format-version cannot be reset: removing it would change the table unsafely")
    client = build_client(reset_table_properties=StubUseCase(error=error))

    response = client.post(f"{BASE}/orders/properties/reset", json={"expected_uuid": "u-1", "keys": ["format-version"]})

    assert (response.status_code, response.json()) == (422, {"detail": str(error)})


def test_reset_table_properties_rejects_unknown_fields():
    """The reset body takes only the expected uuid and the keys."""
    response = build_client().post(
        f"{BASE}/orders/properties/reset", json={"expected_uuid": "u-1", "keys": [], "all": True}
    )

    assert response.status_code == 422
