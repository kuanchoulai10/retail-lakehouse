"""Test the UpdateTablePropertiesService."""

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
from application.domain.model.catalog.table_properties.operation_properties import (
    OperationProperties,
)
from application.domain.model.catalog.table_properties.table_properties import (
    TableProperties,
)
from application.domain.model.catalog.table_properties.write_mode import WriteMode
from application.domain.model.catalog.table_properties.write_properties import (
    WriteProperties,
)
from application.domain.model.catalog.table_schema import TableSchema
from application.port.inbound.catalog.update_table_properties import (
    UpdateTablePropertiesUseCaseInput,
    UpdateTablePropertiesUseCaseOutput,
    UpdateTablePropertiesUseCase,
)
from application.service.catalog.update_table_properties import (
    UpdateTablePropertiesService,
)


def _make_updated_table() -> Table:
    """Build a Table that represents the state after property update."""
    return Table(
        id=TableId(value="default.orders"),
        namespace="default",
        name="orders",
        location="s3://warehouse/default/orders",
        current_snapshot_id=100,
        schema=TableSchema(
            fields=(
                SchemaField(field_id=1, name="id", field_type="long", required=True),
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
            write=WriteProperties(
                merge=OperationProperties(mode=WriteMode.MERGE_ON_READ),
                format=FormatProperties(default="parquet"),
            ),
        ),
    )


def test_implements_use_case():
    """UpdateTablePropertiesService implements UpdateTablePropertiesUseCase."""
    assert issubclass(UpdateTablePropertiesService, UpdateTablePropertiesUseCase)


def test_splits_updates_and_removals():
    """Service splits input into updates (non-None) and removals (None)."""
    writer = MagicMock()
    reader = MagicMock()
    reader.load_table.return_value = _make_updated_table()
    service = UpdateTablePropertiesService(writer=writer, reader=reader)

    service.execute(
        UpdateTablePropertiesUseCaseInput(
            namespace="default",
            table="orders",
            properties={
                "write.merge.mode": "merge-on-read",
                "write.delete.mode": None,
            },
        )
    )

    writer.execute.assert_called_once()
    call_input = writer.execute.call_args[0][0]
    assert call_input.namespace == "default"
    assert call_input.table == "orders"
    assert call_input.updates == {"write.merge.mode": "merge-on-read"}
    assert call_input.removals == ["write.delete.mode"]


def test_returns_updated_properties():
    """Service returns properties dict after update."""
    writer = MagicMock()
    reader = MagicMock()
    reader.load_table.return_value = _make_updated_table()
    service = UpdateTablePropertiesService(writer=writer, reader=reader)

    result = service.execute(
        UpdateTablePropertiesUseCaseInput(
            namespace="default",
            table="orders",
            properties={"write.merge.mode": "merge-on-read"},
        )
    )

    assert isinstance(result, UpdateTablePropertiesUseCaseOutput)
    assert result.properties["write.merge.mode"] == "merge-on-read"
    assert result.properties["write.format.default"] == "parquet"
    reader.load_table.assert_called_once_with("default", "orders")
