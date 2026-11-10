"""Test the Spark where clauses built from the partitions selected for compaction."""

from __future__ import annotations

import pytest

from context.table_maintenance.application.domain.model.shared import (
    PartitionFieldInfo,
    PartitionSpecInfo,
    PartitionStats,
    SpecFilter,
)
from context.table_maintenance.application.domain.service.table import (
    build_partition_filters,
)


def _field(name, column, source_type, transform, field_id=1000):
    return PartitionFieldInfo(
        field_id=field_id, name=name, source_column=column, source_type=source_type, transform=transform
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


def _where(spec, *partitions):
    (result,) = build_partition_filters("iceberg", [spec], list(partitions))
    return result.where


def test_empty_partitions_returns_empty_tuple():
    """No partitions give no filters."""
    assert build_partition_filters("iceberg", [_spec(0)], []) == ()


def test_identity_string_escapes_quotes():
    """An identity string value has its quotes escaped."""
    spec = _spec(0, _field("region", "region", "string", "identity"))
    assert _where(spec, _part(0, "o'neil")) == "(`region` = 'o\\'neil')"


def test_identity_numeric_boolean_decimal_literals():
    """Identity numeric, boolean and decimal values become plain literals."""
    spec = _spec(
        0,
        _field("a", "a", "int", "identity"),
        _field("b", "b", "long", "identity"),
        _field("c", "c", "double", "identity"),
        _field("d", "d", "boolean", "identity"),
        _field("e", "e", "decimal(9,2)", "identity"),
    )
    assert _where(spec, _part(0, 1, -2, 1.5, True, "12.30")) == (
        "(`a` = 1 AND `b` = -2 AND `c` = 1.5 AND `d` = true AND `e` = 12.30)"
    )
    flag = _spec(0, _field("d", "d", "boolean", "identity"))
    assert _where(flag, _part(0, False)) == "(`d` = false)"


def test_identity_date_and_timestamp_literals():
    """Identity date and timestamp values become date and timestamp literals."""
    spec = _spec(
        0,
        _field("d", "d", "date", "identity"),
        _field("t", "t", "timestamp", "identity"),
        _field("z", "z", "timestamptz", "identity"),
    )
    micros = 20385 * 86_400_000_000 + 3_723_000_456
    assert _where(spec, _part(0, 20385, micros, micros)) == (
        "(`d` = DATE '2025-10-24'"
        " AND `t` = TIMESTAMP_NTZ '2025-10-24 01:02:03.000456'"
        " AND `z` = TIMESTAMP '2025-10-24 01:02:03.000456+00:00')"
    )


def test_day_transform_uses_date_literal_and_range():
    """A day partition on a timestamp becomes a half open timestamp range."""
    spec = _spec(0, _field("ts_day", "ts", "timestamptz", "day"))
    assert _where(spec, _part(0, 20385)) == (
        "(`iceberg`.system.days(`ts`) = DATE '2025-10-24'"
        " AND `ts` >= TIMESTAMP '2025-10-24 00:00:00.000000+00:00'"
        " AND `ts` < TIMESTAMP '2025-10-25 00:00:00.000000+00:00')"
    )


def test_day_transform_on_date_column_uses_date_range():
    """A day partition on a date column becomes a date range."""
    spec = _spec(0, _field("d_day", "d", "date", "day"))
    assert _where(spec, _part(0, 20385)) == (
        "(`iceberg`.system.days(`d`) = DATE '2025-10-24' AND `d` >= DATE '2025-10-24' AND `d` < DATE '2025-10-25')"
    )


def test_hour_month_year_use_ints():
    """Hour, month and year partitions are filtered by their integer ranges."""
    hour = _spec(0, _field("h", "ts", "timestamp", "hour"))
    month = _spec(0, _field("m", "ts", "timestamp", "month"))
    year = _spec(0, _field("y", "ts", "timestamp", "year"))
    assert _where(hour, _part(0, 490000)) == (
        "(`iceberg`.system.hours(`ts`) = 490000"
        " AND `ts` >= TIMESTAMP_NTZ '2025-11-24 16:00:00.000000'"
        " AND `ts` < TIMESTAMP_NTZ '2025-11-24 17:00:00.000000')"
    )
    assert _where(month, _part(0, 669)) == (
        "(`iceberg`.system.months(`ts`) = 669"
        " AND `ts` >= TIMESTAMP_NTZ '2025-10-01 00:00:00.000000'"
        " AND `ts` < TIMESTAMP_NTZ '2025-11-01 00:00:00.000000')"
    )
    assert _where(year, _part(0, 55)) == (
        "(`iceberg`.system.years(`ts`) = 55"
        " AND `ts` >= TIMESTAMP_NTZ '2025-01-01 00:00:00.000000'"
        " AND `ts` < TIMESTAMP_NTZ '2026-01-01 00:00:00.000000')"
    )


def test_month_december_rolls_over_year_on_date_column():
    """A December month partition on a date column ends in January of the next year."""
    spec = _spec(0, _field("m", "d", "date", "month"))
    assert _where(spec, _part(0, 671)) == (
        "(`iceberg`.system.months(`d`) = 671 AND `d` >= DATE '2025-12-01' AND `d` < DATE '2026-01-01')"
    )


def test_year_on_date_column():
    """A year partition on a date column becomes a date range."""
    spec = _spec(0, _field("y", "d", "date", "year"))
    assert _where(spec, _part(0, 55)) == (
        "(`iceberg`.system.years(`d`) = 55 AND `d` >= DATE '2025-01-01' AND `d` < DATE '2026-01-01')"
    )


def test_hour_on_date_column_raises():
    """An hour partition on a date column is rejected."""
    spec = _spec(0, _field("h", "d", "date", "hour"))
    with pytest.raises(ValueError):
        _where(spec, _part(0, 1))


def test_bucket_and_truncate():
    """Bucket and truncate partitions use the system bucket and truncate functions."""
    bucket = _spec(0, _field("id_bucket", "id", "long", "bucket[16]"))
    trunc = _spec(0, _field("name_trunc", "name", "string", "truncate[4]"))
    assert _where(bucket, _part(0, 3)) == "(`iceberg`.system.bucket(16, `id`) = 3)"
    assert _where(trunc, _part(0, "abcd")) == "(`iceberg`.system.truncate(4, `name`) = 'abcd')"


def test_truncate_int_source():
    """A truncate partition on an integer column compares the truncated number."""
    spec = _spec(0, _field("n", "n", "int", "truncate[10]"))
    assert _where(spec, _part(0, 20)) == "(`iceberg`.system.truncate(10, `n`) = 20)"


def test_null_partition_value_uses_is_null():
    """A null partition value becomes an IS NULL test."""
    spec = _spec(
        0,
        _field("r", "region", "string", "identity"),
        _field("b", "id", "long", "bucket[16]"),
        _field("d", "ts", "timestamptz", "day"),
    )
    assert _where(spec, _part(0, None, None, None)) == ("(`region` IS NULL AND `id` IS NULL AND `ts` IS NULL)")


def test_multi_field_partition_and_multiple_partitions():
    """Several fields are joined with AND and several partitions with OR."""
    spec = _spec(
        0,
        _field("d", "ts", "timestamptz", "day"),
        _field("b", "id", "long", "bucket[16]"),
    )
    assert _where(spec, _part(0, 20385, 3), _part(0, 20386, 5)) == (
        "(`iceberg`.system.days(`ts`) = DATE '2025-10-24'"
        " AND `ts` >= TIMESTAMP '2025-10-24 00:00:00.000000+00:00'"
        " AND `ts` < TIMESTAMP '2025-10-25 00:00:00.000000+00:00'"
        " AND `iceberg`.system.bucket(16, `id`) = 3)"
        " OR (`iceberg`.system.days(`ts`) = DATE '2025-10-25'"
        " AND `ts` >= TIMESTAMP '2025-10-25 00:00:00.000000+00:00'"
        " AND `ts` < TIMESTAMP '2025-10-26 00:00:00.000000+00:00'"
        " AND `iceberg`.system.bucket(16, `id`) = 5)"
    )


def test_void_fields_are_skipped():
    """Fields with a void transform are left out of the clause."""
    spec = _spec(
        0,
        _field("old", "old", "string", "void"),
        _field("r", "region", "string", "identity"),
    )
    assert _where(spec, _part(0, "x", "eu")) == "(`region` = 'eu')"
    assert _where(spec, _part(0, None, "eu")) == "(`region` = 'eu')"


def test_all_void_spec_yields_empty_where():
    """A spec whose fields are all void gives an empty where clause."""
    spec = _spec(1, _field("old", "old", "string", "void"))
    assert build_partition_filters("iceberg", [spec], [_part(1, None)]) == (SpecFilter(spec_id=1, where=""),)


def test_unpartitioned_spec_yields_empty_where():
    """An unpartitioned spec gives an empty where clause."""
    assert build_partition_filters("iceberg", [_spec(0)], [_part(0)]) == (SpecFilter(spec_id=0, where=""),)


def test_one_filter_per_spec_id():
    """There is one filter per partition spec id."""
    spec0 = _spec(0, _field("r", "region", "string", "identity"))
    spec1 = _spec(1, _field("b", "id", "long", "bucket[8]"))
    result = build_partition_filters("iceberg", [spec1, spec0], [_part(1, 2), _part(0, "eu"), _part(0, "us")])
    assert result == (
        SpecFilter(spec_id=0, where="(`region` = 'eu') OR (`region` = 'us')"),
        SpecFilter(spec_id=1, where="(`iceberg`.system.bucket(8, `id`) = 2)"),
    )


def test_unknown_spec_id_raises():
    """A partition with an unknown spec id is rejected."""
    with pytest.raises(ValueError):
        build_partition_filters("iceberg", [_spec(0)], [_part(5)])


def test_value_count_mismatch_raises():
    """A partition whose value count differs from its spec fields is rejected."""
    spec = _spec(0, _field("r", "region", "string", "identity"))
    with pytest.raises(ValueError):
        _where(spec, _part(0, "a", "b"))


def test_column_quoting_nested_and_backticks():
    """Nested column names are quoted per part and backticks in names are doubled."""
    spec = _spec(
        0,
        _field("n", "a.b", "string", "identity"),
        _field("q", "we`ird", "string", "identity"),
    )
    assert _where(spec, _part(0, "x", "y")) == "(`a`.`b` = 'x' AND `we``ird` = 'y')"


@pytest.mark.parametrize("source_type", ["uuid", "binary", "fixed[4]", "time"])
def test_unsupported_identity_types_raise(source_type):
    """Identity partitions on unsupported column types are rejected."""
    spec = _spec(0, _field("u", "u", source_type, "identity"))
    with pytest.raises(ValueError):
        _where(spec, _part(0, "v"))


@pytest.mark.parametrize("source_type", ["timestamp_ns", "timestamptz_ns"])
def test_nanosecond_timestamp_types_raise(source_type):
    """Partitions on nanosecond timestamp columns are rejected."""
    spec = _spec(0, _field("t", "t", source_type, "day"))
    with pytest.raises(ValueError):
        _where(spec, _part(0, 1))


def test_unknown_transform_raises():
    """A partition transform that is not known is rejected."""
    spec = _spec(0, _field("x", "x", "int", "weird"))
    with pytest.raises(ValueError):
        _where(spec, _part(0, 1))


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("a\\b", "'a\\\\b'"),
        ("abc\\", "'abc\\\\'"),
        ("it's", "'it\\'s'"),
        ("\\'", "'\\\\\\''"),
        ("line1\nline2", "'line1\nline2'"),
    ],
)
def test_string_escaping_for_spark_parser(value, expected):
    """String values are escaped so the Spark parser reads them back unchanged."""
    spec = _spec(0, _field("r", "region", "string", "identity"))
    assert _where(spec, _part(0, value)) == f"(`region` = {expected})"


def test_truncate_string_escapes_backslash():
    """A truncated string value has its backslash escaped."""
    spec = _spec(0, _field("n", "name", "string", "truncate[2]"))
    assert _where(spec, _part(0, "a\\")) == "(`iceberg`.system.truncate(2, `name`) = 'a\\\\')"


def test_clauses_sorted_and_deduplicated():
    """The clauses are sorted and deduplicated, so the order of the partitions does not matter."""
    spec = _spec(0, _field("r", "region", "string", "identity"))
    forward = _where(spec, _part(0, "us"), _part(0, "eu"), _part(0, "us"))
    backward = _where(spec, _part(0, "eu"), _part(0, "us"))
    assert forward == backward == "(`region` = 'eu') OR (`region` = 'us')"


def test_day_on_timestamp_without_zone_uses_ntz_range():
    """A day partition on a timestamp without zone uses a timestamp_ntz range."""
    spec = _spec(0, _field("d", "ts", "timestamp", "day"))
    assert _where(spec, _part(0, 20385)) == (
        "(`iceberg`.system.days(`ts`) = DATE '2025-10-24'"
        " AND `ts` >= TIMESTAMP_NTZ '2025-10-24 00:00:00.000000'"
        " AND `ts` < TIMESTAMP_NTZ '2025-10-25 00:00:00.000000')"
    )


def test_catalog_name_is_backtick_quoted():
    """The catalog name in the system function is backtick quoted."""
    spec = _spec(0, _field("b", "id", "long", "bucket[4]"))
    (result,) = build_partition_filters("my`cat", [spec], [_part(0, 1)])
    assert result.where == "(`my``cat`.system.bucket(4, `id`) = 1)"


def test_pre_1970_values():
    """Month, day and hour values before 1970 are converted to the right ranges."""
    month = _spec(0, _field("m", "d", "date", "month"))
    day = _spec(0, _field("d", "d", "date", "day"))
    hour = _spec(0, _field("h", "ts", "timestamp", "hour"))
    year = _spec(0, _field("y", "d", "date", "year"))
    assert _where(month, _part(0, -1)) == (
        "(`iceberg`.system.months(`d`) = -1 AND `d` >= DATE '1969-12-01' AND `d` < DATE '1970-01-01')"
    )
    assert _where(day, _part(0, -1)) == (
        "(`iceberg`.system.days(`d`) = DATE '1969-12-31' AND `d` >= DATE '1969-12-31' AND `d` < DATE '1970-01-01')"
    )
    assert _where(hour, _part(0, -1)) == (
        "(`iceberg`.system.hours(`ts`) = -1"
        " AND `ts` >= TIMESTAMP_NTZ '1969-12-31 23:00:00.000000'"
        " AND `ts` < TIMESTAMP_NTZ '1970-01-01 00:00:00.000000')"
    )
    assert _where(year, _part(0, -1)) == (
        "(`iceberg`.system.years(`d`) = -1 AND `d` >= DATE '1969-01-01' AND `d` < DATE '1970-01-01')"
    )
