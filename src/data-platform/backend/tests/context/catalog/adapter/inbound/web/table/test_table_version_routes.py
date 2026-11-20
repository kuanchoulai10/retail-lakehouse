"""Test the routes that list a table's schema and partition spec versions and compare any two."""

from __future__ import annotations

from context.catalog.application.exceptions import NotFoundError
from context.catalog.application.port.inbound.table import (
    GetTablePartitionSpecComparisonUseCaseInput,
    GetTablePartitionSpecComparisonUseCaseOutput,
    GetTableSchemaComparisonUseCaseInput,
    GetTableSchemaComparisonUseCaseOutput,
    ListTablePartitionSpecVersionsUseCaseInput,
    ListTablePartitionSpecVersionsUseCaseOutput,
    ListTableSchemaVersionsUseCaseInput,
    ListTableSchemaVersionsUseCaseOutput,
)
from tests.context.catalog.adapter.inbound.web.web_test_support import StubUseCase, build_client

BASE = "/v1/catalogs/sales/namespaces/retail/tables/orders"

SCHEMA_VERSIONS = ListTableSchemaVersionsUseCaseOutput(
    current_schema_id=1,
    items=(
        ListTableSchemaVersionsUseCaseOutput.Version(
            schema_id=1,
            previous_schema_id=0,
            current=True,
            column_count=6,
            changes={
                "added": 5,
                "removed": 0,
                "renamed": 0,
                "type_changed": 0,
                "nullability_changed": 0,
                "doc_changed": 1,
            },
        ),
        ListTableSchemaVersionsUseCaseOutput.Version(
            schema_id=0, previous_schema_id=None, current=False, column_count=3, changes=None
        ),
    ),
)

SPEC_VERSIONS = ListTablePartitionSpecVersionsUseCaseOutput(
    default_spec_id=1,
    items=(
        ListTablePartitionSpecVersionsUseCaseOutput.Version(
            spec_id=1,
            previous_spec_id=0,
            default=True,
            field_count=2,
            changes={"added": 1, "removed": 0, "renamed": 0, "transform_changed": 0},
        ),
        ListTablePartitionSpecVersionsUseCaseOutput.Version(
            spec_id=0, previous_spec_id=None, default=False, field_count=1, changes=None
        ),
    ),
)


def _schema_comparison() -> GetTableSchemaComparisonUseCaseOutput:
    return GetTableSchemaComparisonUseCaseOutput(
        base_schema_id=0,
        schema_id=1,
        items=(
            GetTableSchemaComparisonUseCaseOutput.Field(
                field_id=5,
                depth=1,
                path=("address", "city"),
                previous_path=None,
                type="string",
                previous_type=None,
                required=False,
                previous_required=None,
                doc=None,
                previous_doc=None,
                changes=("added",),
            ),
            GetTableSchemaComparisonUseCaseOutput.Field(
                field_id=2,
                depth=0,
                path=("customer",),
                previous_path=("customer_id",),
                type="long",
                previous_type="int",
                required=False,
                previous_required=False,
                doc=None,
                previous_doc=None,
                changes=("renamed", "type_changed"),
            ),
        ),
    )


def _spec_comparison() -> GetTablePartitionSpecComparisonUseCaseOutput:
    return GetTablePartitionSpecComparisonUseCaseOutput(
        base_spec_id=0,
        spec_id=1,
        items=(
            GetTablePartitionSpecComparisonUseCaseOutput.Field(
                field_id=1001,
                previous_field_id=1000,
                name="order_ts_hour",
                previous_name="order_ts_day",
                source_path=("order_ts",),
                previous_source_path=("order_ts",),
                transform="hour",
                previous_transform="day",
                changes=("transform_changed",),
                expression="hour(order_ts)",
                previous_expression="day(order_ts)",
            ),
        ),
    )


def test_list_schema_versions_returns_the_versions_with_their_counts():
    """The list route answers the current id and each version with its change counts, null for the first."""
    stub = StubUseCase(SCHEMA_VERSIONS)

    response = build_client(list_table_schema_versions=stub).get(f"{BASE}/schema-versions")

    assert response.status_code == 200
    assert response.json() == {
        "current_schema_id": 1,
        "versions": [
            {
                "schema_id": 1,
                "previous_schema_id": 0,
                "current": True,
                "column_count": 6,
                "changes": {
                    "added": 5,
                    "removed": 0,
                    "renamed": 0,
                    "type_changed": 0,
                    "nullability_changed": 0,
                    "doc_changed": 1,
                },
            },
            {"schema_id": 0, "previous_schema_id": None, "current": False, "column_count": 3, "changes": None},
        ],
    }
    assert stub.requests == [ListTableSchemaVersionsUseCaseInput(catalog="sales", namespace=("retail",), name="orders")]


def test_schema_comparison_returns_each_field_with_its_changes():
    """The comparison route answers the base, the schema and one row per field, paths as segment lists."""
    stub = StubUseCase(_schema_comparison())

    response = build_client(get_table_schema_comparison=stub).get(f"{BASE}/schema-versions/1/comparison")

    assert response.status_code == 200
    body = response.json()
    assert (body["base_schema_id"], body["schema_id"]) == (0, 1)
    assert body["fields"][0] == {
        "field_id": 5,
        "depth": 1,
        "path": ["address", "city"],
        "previous_path": None,
        "type": "string",
        "previous_type": None,
        "required": False,
        "previous_required": None,
        "doc": None,
        "previous_doc": None,
        "changes": ["added"],
    }
    assert body["fields"][1]["previous_path"] == ["customer_id"]
    assert body["fields"][1]["changes"] == ["renamed", "type_changed"]


def test_schema_comparison_passes_the_base_or_none():
    """``?base=0`` reaches the input as base_schema_id 0; no base reaches it as None."""
    stub = StubUseCase(_schema_comparison())
    client = build_client(get_table_schema_comparison=stub)

    client.get(f"{BASE}/schema-versions/1/comparison?base=0")
    client.get(f"{BASE}/schema-versions/1/comparison")

    assert stub.requests == [
        GetTableSchemaComparisonUseCaseInput(
            catalog="sales", namespace=("retail",), name="orders", schema_id=1, base_schema_id=0
        ),
        GetTableSchemaComparisonUseCaseInput(
            catalog="sales", namespace=("retail",), name="orders", schema_id=1, base_schema_id=None
        ),
    ]


def test_schema_comparison_rejects_a_base_that_is_not_a_number():
    """A base or schema id that is not an integer is 422 and reaches no use case."""
    stub = StubUseCase(_schema_comparison())
    client = build_client(get_table_schema_comparison=stub)

    assert client.get(f"{BASE}/schema-versions/1/comparison?base=x").status_code == 422
    assert client.get(f"{BASE}/schema-versions/x/comparison").status_code == 422
    assert stub.requests == []


def test_schema_comparison_of_an_unknown_version_is_404_with_the_message():
    """A NotFoundError is a 404 carrying its message."""
    stub = StubUseCase(error=NotFoundError("schema 9 not found in table orders"))

    response = build_client(get_table_schema_comparison=stub).get(f"{BASE}/schema-versions/9/comparison")

    assert (response.status_code, response.json()) == (404, {"detail": "schema 9 not found in table orders"})


def test_list_partition_spec_versions_marks_the_default():
    """The list route answers the default id and each version with its field count and change counts."""
    stub = StubUseCase(SPEC_VERSIONS)

    response = build_client(list_table_partition_spec_versions=stub).get(f"{BASE}/partition-spec-versions")

    assert response.status_code == 200
    assert response.json() == {
        "default_spec_id": 1,
        "versions": [
            {
                "spec_id": 1,
                "previous_spec_id": 0,
                "default": True,
                "field_count": 2,
                "changes": {"added": 1, "removed": 0, "renamed": 0, "transform_changed": 0},
            },
            {"spec_id": 0, "previous_spec_id": None, "default": False, "field_count": 1, "changes": None},
        ],
    }
    assert stub.requests == [
        ListTablePartitionSpecVersionsUseCaseInput(catalog="sales", namespace=("retail",), name="orders")
    ]


def test_partition_spec_comparison_returns_each_field_with_its_expression():
    """The comparison route answers one row per field with both expressions."""
    stub = StubUseCase(_spec_comparison())

    response = build_client(get_table_partition_spec_comparison=stub).get(
        f"{BASE}/partition-spec-versions/1/comparison?base=0"
    )

    assert response.status_code == 200
    assert response.json() == {
        "base_spec_id": 0,
        "spec_id": 1,
        "fields": [
            {
                "field_id": 1001,
                "previous_field_id": 1000,
                "name": "order_ts_hour",
                "previous_name": "order_ts_day",
                "source_path": ["order_ts"],
                "previous_source_path": ["order_ts"],
                "transform": "hour",
                "previous_transform": "day",
                "changes": ["transform_changed"],
                "expression": "hour(order_ts)",
                "previous_expression": "day(order_ts)",
            }
        ],
    }
    assert stub.requests == [
        GetTablePartitionSpecComparisonUseCaseInput(
            catalog="sales", namespace=("retail",), name="orders", spec_id=1, base_spec_id=0
        )
    ]


def test_partition_spec_comparison_without_a_base_passes_none_and_rejects_a_bad_one():
    """No base reaches the input as None; a base that is not a number is 422."""
    stub = StubUseCase(_spec_comparison())
    client = build_client(get_table_partition_spec_comparison=stub)

    assert client.get(f"{BASE}/partition-spec-versions/1/comparison").status_code == 200
    assert client.get(f"{BASE}/partition-spec-versions/1/comparison?base=x").status_code == 422
    assert [request.base_spec_id for request in stub.requests] == [None]


def test_version_routes_split_the_namespace_on_the_unit_separator():
    """A namespace of two parts, joined by %1F in the path, reaches the input as two parts."""
    stubs = {
        "list_table_schema_versions": StubUseCase(SCHEMA_VERSIONS),
        "get_table_schema_comparison": StubUseCase(_schema_comparison()),
        "list_table_partition_spec_versions": StubUseCase(SPEC_VERSIONS),
        "get_table_partition_spec_comparison": StubUseCase(_spec_comparison()),
    }
    client = build_client(**stubs)
    base = "/v1/catalogs/sales/namespaces/a%1Fb/tables/orders"

    for path in (
        "schema-versions",
        "schema-versions/1/comparison",
        "partition-spec-versions",
        "partition-spec-versions/1/comparison",
    ):
        assert client.get(f"{base}/{path}").status_code == 200

    assert [stub.requests[0].namespace for stub in stubs.values()] == [("a", "b")] * 4


def test_version_routes_answer_404_for_a_missing_table():
    """A NotFoundError from any of the four is a 404 with its message."""
    error = NotFoundError("table orders not found in namespace ['retail'] of catalog sales")
    client = build_client(
        list_table_schema_versions=StubUseCase(error=error),
        list_table_partition_spec_versions=StubUseCase(error=error),
        get_table_partition_spec_comparison=StubUseCase(error=error),
    )

    for path in ("schema-versions", "partition-spec-versions", "partition-spec-versions/1/comparison"):
        response = client.get(f"{BASE}/{path}")
        assert (response.status_code, response.json()) == (404, {"detail": str(error)})
