"""Test the ListTagsService."""

from __future__ import annotations

from unittest.mock import MagicMock

from core.application.domain.model.catalog.branch import Branch
from core.application.domain.model.catalog.branch_id import BranchId
from core.application.domain.model.catalog.schema_field import SchemaField
from core.application.domain.model.catalog.snapshot import Snapshot
from core.application.domain.model.catalog.snapshot_summary import SnapshotSummary
from core.application.domain.model.catalog.table import Table
from core.application.domain.model.catalog.table_id import TableId
from core.application.domain.model.catalog.table_schema import TableSchema
from core.application.domain.model.catalog.tag import Tag
from core.application.service.catalog.list_tags import ListTagsService
from core.application.port.inbound.catalog.list_tags import (
    ListTagsInput,
    ListTagsOutput,
    ListTagsUseCase,
)


def _make_table_with_tags() -> Table:
    """Build a Table with two tags."""
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
        branches=(Branch(id=BranchId(value="main"), snapshot_id=100),),
        tags=(
            Tag(name="v1.0", snapshot_id=100, max_ref_age_ms=86400000),
            Tag(name="v2.0", snapshot_id=100),
        ),
        properties={},
    )


def test_implements_use_case():
    """ListTagsService implements ListTagsUseCase."""
    assert issubclass(ListTagsService, ListTagsUseCase)


def test_returns_tags():
    """Service loads table and returns tag list."""
    reader = MagicMock()
    reader.load_table.return_value = _make_table_with_tags()
    service = ListTagsService(reader)

    result = service.execute(ListTagsInput(namespace="default", table="orders"))

    assert isinstance(result, ListTagsOutput)
    assert len(result.tags) == 2
    assert result.tags[0].name == "v1.0"
    assert result.tags[0].max_ref_age_ms == 86400000
    assert result.tags[1].name == "v2.0"
    assert result.tags[1].max_ref_age_ms is None
