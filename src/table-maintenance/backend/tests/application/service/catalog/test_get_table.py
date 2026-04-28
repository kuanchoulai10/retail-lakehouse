"""Test the GetTableService."""

from __future__ import annotations

from unittest.mock import MagicMock

from application.domain.model.catalog.branch import Branch
from application.domain.model.catalog.branch_id import BranchId
from application.domain.model.catalog.schema_field import SchemaField
from application.domain.model.catalog.snapshot import Snapshot
from application.domain.model.catalog.snapshot_summary import SnapshotSummary
from application.domain.model.catalog.table import Table
from application.domain.model.catalog.table_id import TableId
from application.domain.model.catalog.table_properties.format_properties import (
    FormatProperties,
)
from application.domain.model.catalog.table_properties.table_properties import (
    TableProperties,
)
from application.domain.model.catalog.table_properties.write_properties import (
    WriteProperties,
)
from application.domain.model.catalog.table_schema import TableSchema
from application.service.catalog.get_table import GetTableService
from application.port.inbound.catalog.get_table import (
    GetTableUseCaseInput,
    GetTableUseCaseOutput,
    GetTableUseCase,
)


def _make_table() -> Table:
    """Build a Table domain object for testing."""
    return Table(
        id=TableId(value="default.orders"),
        namespace="default",
        name="orders",
        location="s3://warehouse/default/orders",
        current_snapshot_id=100,
        schema=TableSchema(
            fields=(
                SchemaField(
                    field_id=1, name="order_id", field_type="long", required=True
                ),
                SchemaField(
                    field_id=2, name="amount", field_type="double", required=False
                ),
            ),
        ),
        snapshots=(
            Snapshot(
                snapshot_id=100,
                parent_id=None,
                timestamp_ms=0,
                summary=SnapshotSummary(data={}),
            ),
        ),
        branches=(Branch(id=BranchId(value="main"), snapshot_id=100),),
        tags=(),
        properties=TableProperties(
            write=WriteProperties(format=FormatProperties(default="parquet")),
        ),
    )


def test_implements_use_case():
    """GetTableService implements GetTableUseCase."""
    assert issubclass(GetTableService, GetTableUseCase)


def test_returns_table_metadata():
    """Service loads table and returns metadata output."""
    reader = MagicMock()
    reader.load_table.return_value = _make_table()
    service = GetTableService(reader)

    result = service.execute(GetTableUseCaseInput(namespace="default", table="orders"))

    assert isinstance(result, GetTableUseCaseOutput)
    assert result.name == "orders"
    assert result.namespace == "default"
    assert result.location == "s3://warehouse/default/orders"
    assert result.current_snapshot_id == 100
    assert len(result.schema.fields) == 2
    assert result.schema.fields[0].name == "order_id"
    assert result.properties == {"write.format.default": "parquet"}
    reader.load_table.assert_called_once_with("default", "orders")
