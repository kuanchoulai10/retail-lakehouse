"""Tests for the partition_label domain service."""

from __future__ import annotations

import pytest

from context.table_maintenance.application.domain.model.compaction_candidate import PartitionKey
from context.table_maintenance.application.domain.model.shared import PartitionFieldInfo, PartitionSpecInfo
from context.table_maintenance.application.domain.service.compaction_candidate import partition_label


def _field(name: str, source_type: str, transform: str) -> PartitionFieldInfo:
    return PartitionFieldInfo(
        field_id=1000, name=name, source_column=name, source_type=source_type, transform=transform
    )


def test_identity_and_day_fields_read_as_field_value_pairs():
    """An identity value reads as itself and a day as its date."""
    spec = PartitionSpecInfo(
        spec_id=0, fields=(_field("order_ts_day", "timestamptz", "day"), _field("region", "string", "identity"))
    )
    assert partition_label((spec,), PartitionKey(spec_id=0, values=(20362, "o'neil"))) == (
        "order_ts_day=2025-10-01, region=o'neil"
    )


@pytest.mark.parametrize(
    ("source_type", "transform", "value", "text"),
    [
        ("timestamp", "month", 669, "2025-10"),
        ("timestamp", "year", 55, "2025"),
        ("timestamp", "hour", 488688, "2025-10-01-00"),
        ("date", "identity", 20362, "2025-10-01"),
        ("timestamp", "identity", 1759276800000000, "2025-10-01T00:00:00"),
        ("long", "bucket[4]", 3, "3"),
        ("string", "truncate[2]", "eu", "eu"),
        ("string", "identity", None, "null"),
        ("boolean", "identity", True, "true"),
    ],
)
def test_each_transform_reads_as_people_write_it(source_type, transform, value, text):
    """Time transforms read as calendar values, others as their value."""
    spec = PartitionSpecInfo(spec_id=0, fields=(_field("f", source_type, transform),))
    assert partition_label((spec,), PartitionKey(spec_id=0, values=(value,))) == f"f={text}"


def test_whole_table_reads_as_whole_table():
    """The whole-table key reads as the whole table."""
    assert partition_label((), PartitionKey.whole_table()) == "whole table"


def test_void_fields_are_left_out_and_an_unknown_spec_reads_its_values():
    """A dropped (void) field is not shown; a spec missing from the table falls back to the raw values."""
    spec = PartitionSpecInfo(
        spec_id=0, fields=(_field("old", "string", "void"), _field("region", "string", "identity"))
    )
    assert partition_label((spec,), PartitionKey(spec_id=0, values=(None, "eu"))) == "region=eu"
    assert partition_label((spec,), PartitionKey(spec_id=9, values=("x", 1))) == "spec 9: x, 1"
