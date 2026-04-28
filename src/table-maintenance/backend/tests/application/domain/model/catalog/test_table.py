"""Test the Table aggregate root."""

from __future__ import annotations

from base import AggregateRoot
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


def _make_table(**overrides) -> Table:
    """Build a Table with sensible defaults, overridable per test."""
    defaults = {
        "id": TableId(value="default.orders"),
        "namespace": "default",
        "name": "orders",
        "location": "s3://warehouse/default/orders",
        "current_snapshot_id": 100,
        "schema": TableSchema(
            fields=(
                SchemaField(field_id=1, name="id", field_type="long", required=True),
            )
        ),
        "snapshots": (
            Snapshot(
                snapshot_id=100,
                parent_id=None,
                timestamp_ms=0,
                summary=SnapshotSummary(data={}),
            ),
        ),
        "branches": (Branch(id=BranchId(value="main"), snapshot_id=100),),
        "tags": (),
        "properties": TableProperties(
            write=WriteProperties(format=FormatProperties(default="parquet")),
        ),
    }
    defaults.update(overrides)
    return Table(**defaults)


def test_table_is_aggregate_root():
    """Table extends AggregateRoot."""
    assert issubclass(Table, AggregateRoot)


def test_table_fields():
    """Table stores all fields correctly."""
    t = _make_table()
    assert t.namespace == "default"
    assert t.name == "orders"
    assert t.location == "s3://warehouse/default/orders"
    assert t.current_snapshot_id == 100
    assert len(t.schema.fields) == 1
    assert len(t.snapshots) == 1
    assert len(t.branches) == 1
    assert len(t.tags) == 0


def test_table_equality_by_id():
    """Same TableId = equal, regardless of other fields."""
    a = _make_table(name="orders")
    b = _make_table(name="different")
    assert a == b


def test_table_inequality_by_id():
    """Different TableId = not equal."""
    a = _make_table(id=TableId(value="a.b"))
    b = _make_table(id=TableId(value="c.d"))
    assert a != b


def test_table_snapshots_are_tuple():
    """Snapshots collection is a tuple."""
    t = _make_table()
    assert isinstance(t.snapshots, tuple)


def test_table_branches_are_tuple():
    """Branches collection is a tuple."""
    t = _make_table()
    assert isinstance(t.branches, tuple)


def test_table_tags_are_tuple():
    """Tags collection is a tuple."""
    t = _make_table()
    assert isinstance(t.tags, tuple)
