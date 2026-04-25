"""Tests for get table metadata endpoint."""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.adapter.inbound.web import router
from core.application.port.inbound.catalog.get_table.output import (
    GetTableOutput,
    GetTableSchemaFieldOutput,
    GetTableSchemaOutput,
)
from api.dependencies.use_cases import get_get_table_use_case


def _make_client(use_case: MagicMock) -> TestClient:
    """Provide a test client with the use case overridden."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_get_table_use_case] = lambda: use_case
    return TestClient(app)


SAMPLE_OUTPUT = GetTableOutput(
    name="orders",
    namespace="default",
    location="s3://warehouse/default/orders",
    current_snapshot_id=123,
    schema=GetTableSchemaOutput(
        fields=[
            GetTableSchemaFieldOutput(
                field_id=1, name="order_id", field_type="long", required=True
            ),
        ],
    ),
    properties={"write.format.default": "parquet"},
)


def test_get_table_returns_200():
    """Return 200 with table metadata."""
    use_case = MagicMock()
    use_case.execute.return_value = SAMPLE_OUTPUT
    client = _make_client(use_case)

    response = client.get("/v1/catalogs/iceberg/namespaces/default/tables/orders")

    assert response.status_code == 200
    body = response.json()
    assert body["table"] == "orders"
    assert body["namespace"] == "default"
    assert body["location"] == "s3://warehouse/default/orders"
    assert body["current_snapshot_id"] == 123
    assert len(body["schema"]["fields"]) == 1
    assert body["schema"]["fields"][0]["name"] == "order_id"
