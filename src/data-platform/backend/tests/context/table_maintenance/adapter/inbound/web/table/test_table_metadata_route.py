"""Test the table metadata route with a stub use case."""

from __future__ import annotations

import dataclasses

from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.table import (
    GetTableMetadataUseCaseInput,
    GetTableMetadataUseCaseOutput,
)
from tests.context.table_maintenance.adapter.inbound.web.web_test_support import (
    NOW,
    StubUseCase,
    build_client,
)


def _output() -> GetTableMetadataUseCaseOutput:
    return GetTableMetadataUseCaseOutput(
        uuid="u-1",
        format_version=2,
        location="s3://w/orders",
        properties={"a": "b"},
        schema_fields=[{"field_id": 1, "name": "id", "type": "long", "required": True}],
        specs=[],
        current_snapshot_id=7,
        snapshot_count=3,
        last_committed_at=NOW,
        total_records=10,
        total_data_files=2,
        total_delete_files=None,
        total_files_size_bytes=2048,
    )


def test_get_metadata_returns_200() -> None:
    stub = StubUseCase(_output())
    client = build_client(get_table_metadata=stub)

    response = client.get("/v1/tables/u-1/metadata")

    body = response.json()
    assert response.status_code == 200
    assert body["total_records"] == 10
    assert body["total_delete_files"] is None
    assert body["schema_fields"][0]["name"] == "id"
    assert body["last_committed_at"].startswith("2026-10-24T12:00:00")
    assert stub.requests == [GetTableMetadataUseCaseInput(uuid="u-1")]


def test_get_metadata_returns_large_snapshot_id_as_exact_string() -> None:
    output = dataclasses.replace(_output(), current_snapshot_id=3051729675574597004)
    client = build_client(get_table_metadata=StubUseCase(output))

    body = client.get("/v1/tables/u-1/metadata").json()

    assert body["current_snapshot_id"] == "3051729675574597004"


def test_get_metadata_without_snapshot_returns_null_id() -> None:
    output = dataclasses.replace(_output(), current_snapshot_id=None)
    client = build_client(get_table_metadata=StubUseCase(output))

    body = client.get("/v1/tables/u-1/metadata").json()

    assert body["current_snapshot_id"] is None


def test_get_metadata_404_detail() -> None:
    message = "table iceberg.sales.orders is not in the catalog"
    client = build_client(get_table_metadata=StubUseCase(error=NotFoundError(message)))

    response = client.get("/v1/tables/u-1/metadata")

    assert response.status_code == 404
    assert response.json()["detail"] == message
