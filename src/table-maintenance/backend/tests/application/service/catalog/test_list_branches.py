"""Test the ListBranchesService."""

from __future__ import annotations

from unittest.mock import MagicMock

from application.domain.model.catalog.branch import Branch
from application.domain.model.catalog.branch_id import BranchId
from application.domain.model.catalog.retention_policy import RetentionPolicy
from application.domain.model.catalog.schema_field import SchemaField
from application.domain.model.catalog.snapshot import Snapshot
from application.domain.model.catalog.snapshot_summary import SnapshotSummary
from application.domain.model.catalog.table import Table
from application.domain.model.catalog.table_id import TableId
from application.domain.model.catalog.table_schema import TableSchema
from application.service.catalog.list_branches import ListBranchesService
from application.port.inbound.catalog.list_branches import (
    ListBranchesInput,
    ListBranchesOutput,
    ListBranchesUseCase,
)


def _make_table_with_branches() -> Table:
    """Build a Table with two branches."""
    return Table(
        id=TableId(value="default.orders"),
        namespace="default",
        name="orders",
        location="s3://warehouse/default/orders",
        current_snapshot_id=100,
        schema=TableSchema(
            fields=(
                SchemaField(field_id=1, name="id", field_type="long", required=True),
            )
        ),
        snapshots=(
            Snapshot(
                snapshot_id=100,
                parent_id=None,
                timestamp_ms=0,
                summary=SnapshotSummary(data={}),
            ),
        ),
        branches=(
            Branch(
                id=BranchId(value="main"),
                snapshot_id=100,
                retention=RetentionPolicy(
                    max_snapshot_age_ms=86400000, min_snapshots_to_keep=5
                ),
            ),
            Branch(id=BranchId(value="audit"), snapshot_id=100),
        ),
        tags=(),
        properties={},
    )


def test_implements_use_case():
    """ListBranchesService implements ListBranchesUseCase."""
    assert issubclass(ListBranchesService, ListBranchesUseCase)


def test_returns_branches():
    """Service loads table and returns branch list."""
    reader = MagicMock()
    reader.load_table.return_value = _make_table_with_branches()
    service = ListBranchesService(reader)

    result = service.execute(ListBranchesInput(namespace="default", table="orders"))

    assert isinstance(result, ListBranchesOutput)
    assert len(result.branches) == 2
    assert result.branches[0].name == "main"
    assert result.branches[0].max_snapshot_age_ms == 86400000
    assert result.branches[0].min_snapshots_to_keep == 5
    assert result.branches[1].name == "audit"
    assert result.branches[1].max_snapshot_age_ms is None
