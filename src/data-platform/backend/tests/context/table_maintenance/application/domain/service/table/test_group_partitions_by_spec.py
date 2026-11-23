"""Test grouping the partitions selected for compaction by their partition spec."""

from __future__ import annotations

import pytest

from context.table_maintenance.application.domain.model.shared import (
    PartitionFieldInfo,
    PartitionSpecInfo,
    PartitionStats,
    SpecPartitions,
)
from context.table_maintenance.application.domain.service.table import group_partitions_by_spec


def _field(column, source_type, transform, field_id=1000):
    return PartitionFieldInfo(
        field_id=field_id, name=column, source_column=column, source_type=source_type, transform=transform
    )


def _spec(spec_id, *fields):
    return PartitionSpecInfo(spec_id=spec_id, fields=tuple(fields))


def _part(spec_id, *values):
    return PartitionStats(
        spec_id=spec_id,
        values=tuple(values),
        data_file_count=1,
        position_delete_file_count=0,
        equality_delete_file_count=0,
        total_data_file_size_bytes=1,
    )


REGION = _spec(0, _field("region", "string", "identity"))
BUCKET = _spec(1, _field("id", "long", "bucket[8]"))


def test_no_partitions_give_no_selection():
    """Nothing selected means nothing to scope."""
    assert group_partitions_by_spec([REGION], []) == ()


def test_partitions_are_grouped_per_spec_and_sorted_by_spec_id():
    """Each spec gets one entry holding its partition values in the order they were selected."""
    result = group_partitions_by_spec([BUCKET, REGION], [_part(1, 2), _part(0, "eu"), _part(0, "us")])
    assert result == (
        SpecPartitions(spec=REGION, values=(("eu",), ("us",))),
        SpecPartitions(spec=BUCKET, values=((2,),)),
    )


@pytest.mark.parametrize(
    "spec",
    [_spec(0), _spec(0, _field("old", "string", "void"))],
    ids=["no fields", "only void fields"],
)
def test_a_partition_of_an_unpartitioned_spec_means_the_whole_table(spec):
    """A spec with nothing to filter on cannot scope a compaction, so the whole table is compacted."""
    other = _spec(1, _field("region", "string", "identity"))
    partitions = [_part(1, "eu"), _part(0, *(None for _ in spec.fields))]
    assert group_partitions_by_spec([spec, other], partitions) == ()


def test_void_fields_take_any_value():
    """A void field filters nothing, so its value is never checked."""
    spec = _spec(0, _field("old", "string", "void"), _field("region", "string", "identity"))
    (result,) = group_partitions_by_spec([spec], [_part(0, 42, "eu")])
    assert result.values == ((42, "eu"),)


def test_null_values_are_accepted_for_any_type():
    """A null value is a match on null, whatever the column type."""
    spec = _spec(0, _field("u", "uuid", "identity"), _field("id", "long", "bucket[4]", 1001))
    (result,) = group_partitions_by_spec([spec], [_part(0, None, None)])
    assert result.values == ((None, None),)


@pytest.mark.parametrize(
    ("spec", "partition", "message"),
    [
        (REGION, _part(5), "Unknown partition spec id 5"),
        (REGION, _part(0, "a", "b"), "Partition has 2 values but spec 0 has 1 fields"),
        (_spec(0, _field("d", "date", "hour")), _part(0, 1), "hour transform is not valid on a date column"),
        (_spec(0, _field("u", "uuid", "identity")), _part(0, "v"), "Unsupported partition source type 'uuid'"),
        (_spec(0, _field("u", "binary", "identity")), _part(0, "v"), "Unsupported partition source type 'binary'"),
        (
            _spec(0, _field("u", "fixed[4]", "identity")),
            _part(0, "v"),
            "Unsupported partition source type 'fixed\\[4\\]'",
        ),
        (_spec(0, _field("u", "time", "identity")), _part(0, "v"), "Unsupported partition source type 'time'"),
        (
            _spec(0, _field("t", "timestamp_ns", "day")),
            _part(0, None),
            "Nanosecond source type 'timestamp_ns' is not supported",
        ),
        (
            _spec(0, _field("t", "timestamptz_ns", "identity")),
            _part(0, 1),
            "Nanosecond source type 'timestamptz_ns' is not supported",
        ),
        (_spec(0, _field("x", "int", "weird")), _part(0, 1), "Unsupported partition transform 'weird'"),
        (_spec(0, _field("x", "string", "day")), _part(0, 1), "Time transform 'day' on unsupported type 'string'"),
        (_spec(0, _field("x", "long", "identity")), _part(0, "1"), "Expected an integer partition value"),
        (_spec(0, _field("x", "long", "identity")), _part(0, True), "Expected an integer partition value"),
        (_spec(0, _field("x", "long", "bucket[4]")), _part(0, 1.0), "Expected an integer partition value"),
        (_spec(0, _field("x", "double", "identity")), _part(0, "1"), "Expected a number for double"),
        (_spec(0, _field("x", "double", "identity")), _part(0, float("nan")), "Non-finite double value"),
        (_spec(0, _field("x", "decimal(9,2)", "identity")), _part(0, "1e5"), "Invalid decimal value"),
        (_spec(0, _field("x", "string", "identity")), _part(0, 1), "Expected a string"),
        (_spec(0, _field("x", "string", "truncate[2]")), _part(0, 1), "Expected a string"),
        (_spec(0, _field("x", "boolean", "identity")), _part(0, 1), "Expected a boolean"),
        (_spec(0, _field("x", "date", "day")), _part(0, 10**9), "day value 1000000000 is out of range"),
        (_spec(0, _field("x", "date", "month")), _part(0, 10**6), "month value 1000000 is out of range"),
        (_spec(0, _field("x", "timestamp", "year")), _part(0, -(10**4)), "year value -10000 is out of range"),
        (_spec(0, _field("x", "timestamptz", "hour")), _part(0, 10**12), "hour value 1000000000000 is out of range"),
    ],
)
def test_a_selection_the_call_cannot_express_is_refused(spec, partition, message):
    """What the old where builder refused is still refused, with the same reason, before any job is built."""
    with pytest.raises(ValueError, match=message):
        group_partitions_by_spec([spec], [partition])


@pytest.mark.parametrize(
    ("source_type", "value"),
    [("date", 10**9), ("timestamp", 10**20), ("timestamptz", -(10**20))],
)
def test_an_identity_time_value_out_of_range_is_refused(source_type, value):
    """An identity date or timestamp no calendar can hold is refused, not left to fail later."""
    spec = _spec(0, _field("x", source_type, "identity"))
    with pytest.raises(ValueError, match=f"{source_type} value {value} is out of range"):
        group_partitions_by_spec([spec], [_part(0, value)])
