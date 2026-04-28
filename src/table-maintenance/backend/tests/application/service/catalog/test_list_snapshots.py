"""Test the ListSnapshotsService."""

from __future__ import annotations

from unittest.mock import MagicMock

from application.domain.model.catalog.branch import Branch
from application.domain.model.catalog.branch_id import BranchId
from application.domain.model.catalog.schema_field import SchemaField
from application.domain.model.catalog.snapshot import Snapshot
from application.domain.model.catalog.snapshot_summary import SnapshotSummary
from application.domain.model.catalog.table import Table
from application.domain.model.catalog.table_id import TableId
from application.domain.model.catalog.table_properties.table_properties import (
    TableProperties,
)
from application.domain.model.catalog.table_schema import TableSchema
from application.service.catalog.list_snapshots import ListSnapshotsService
from application.port.inbound.catalog.list_snapshots import (
    ListSnapshotsInput,
    ListSnapshotsOutput,
    ListSnapshotsUseCase,
)


def _make_table_with_snapshots() -> Table:
    """Build a Table with two snapshots."""
    return Table(
        id=TableId(value="default.orders"),
        namespace="default",
        name="orders",
        location="s3://warehouse/default/orders",
        current_snapshot_id=200,
        schema=TableSchema(
            fields=(
                SchemaField(field_id=1, name="id", field_type="long", required=True),
            )
        ),
        snapshots=(
            Snapshot(
                snapshot_id=100,
                parent_id=None,
                timestamp_ms=1000,
                summary=SnapshotSummary(data={"operation": "append"}),
            ),
            Snapshot(
                snapshot_id=200,
                parent_id=100,
                timestamp_ms=2000,
                summary=SnapshotSummary(data={"operation": "replace"}),
            ),
        ),
        branches=(Branch(id=BranchId(value="main"), snapshot_id=200),),
        tags=(),
        properties=TableProperties(),
    )


def test_implements_use_case():
    """ListSnapshotsService implements ListSnapshotsUseCase."""
    assert issubclass(ListSnapshotsService, ListSnapshotsUseCase)


def test_returns_snapshots():
    """Service loads table and returns snapshot list."""
    reader = MagicMock()
    reader.load_table.return_value = _make_table_with_snapshots()
    service = ListSnapshotsService(reader)

    result = service.execute(ListSnapshotsInput(namespace="default", table="orders"))

    assert isinstance(result, ListSnapshotsOutput)
    assert len(result.snapshots) == 2
    assert result.snapshots[0].snapshot_id == 100
    assert result.snapshots[0].summary == {"operation": "append"}
    assert result.snapshots[1].parent_id == 100
