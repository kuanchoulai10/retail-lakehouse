"""Test the DefaultPartitionFieldNames policy: the names Iceberg's writers give a partition field by default."""

from __future__ import annotations

import pytest

from context.catalog.application.domain.model.table import (
    DefaultPartitionFieldNames,
    PartitionTransform,
    PartitionTransformKind,
)

NAMES = DefaultPartitionFieldNames()
IDENTITY = PartitionTransform(kind=PartitionTransformKind.IDENTITY)
BUCKET_16 = PartitionTransform(kind=PartitionTransformKind.BUCKET, argument=16)
TRUNCATE_4 = PartitionTransform(kind=PartitionTransformKind.TRUNCATE, argument=4)


def test_identity_is_named_after_its_source_column():
    """An identity field takes its column's name, and nothing else."""
    assert NAMES.is_default("region", IDENTITY, ("region",))
    assert not NAMES.is_default("region_identity", IDENTITY, ("region",))


@pytest.mark.parametrize("kind", ["year", "month", "day", "hour"])
def test_a_time_transform_appends_its_unit(kind: str):
    """A year, month, day or hour field takes the column's name and ``_<unit>``."""
    transform = PartitionTransform(kind=PartitionTransformKind(kind))
    assert NAMES.is_default(f"order_ts_{kind}", transform, ("order_ts",))
    assert not NAMES.is_default("order_ts", transform, ("order_ts",))


def test_bucket_without_its_number_is_the_create_table_form():
    """A bucket field created with the table is named ``<column>_bucket``."""
    assert NAMES.is_default("customer_id_bucket", BUCKET_16, ("customer_id",))


def test_bucket_with_its_number_is_the_added_field_form():
    """A bucket field added later is named ``<column>_bucket_<N>``, with its own N only."""
    assert NAMES.is_default("customer_id_bucket_16", BUCKET_16, ("customer_id",))
    assert not NAMES.is_default("customer_id_bucket_32", BUCKET_16, ("customer_id",))


def test_truncate_without_its_width_is_the_create_table_form():
    """A truncate field created with the table is named ``<column>_trunc``."""
    assert NAMES.is_default("sku_trunc", TRUNCATE_4, ("sku",))


def test_truncate_with_its_width_is_the_added_field_form():
    """A truncate field added later is named ``<column>_trunc_<W>``, with its own W only."""
    assert NAMES.is_default("sku_trunc_4", TRUNCATE_4, ("sku",))
    assert not NAMES.is_default("sku_trunc_8", TRUNCATE_4, ("sku",))
    assert not NAMES.is_default("sku_truncate_4", TRUNCATE_4, ("sku",))


def test_a_nested_source_column_is_named_by_its_dotted_path():
    """A nested column's default name starts with its full path joined by dots."""
    day = PartitionTransform(kind=PartitionTransformKind.DAY)
    assert NAMES.is_default("address.zip_day", day, ("address", "zip"))
    assert not NAMES.is_default("address_zip_day", day, ("address", "zip"))


def test_void_unknown_and_an_unknown_column_have_no_default_name():
    """Nothing is a default name for a void or unknown transform, or for a column no schema holds."""
    void = PartitionTransform(kind=PartitionTransformKind.VOID)
    unknown = PartitionTransform(kind=PartitionTransformKind.UNKNOWN, raw="zorder")
    assert not NAMES.is_default("order_ts_void", void, ("order_ts",))
    assert not NAMES.is_default("order_ts", void, ("order_ts",))
    assert not NAMES.is_default("order_ts_zorder", unknown, ("order_ts",))
    assert not NAMES.is_default("order_ts_day", PartitionTransform(kind=PartitionTransformKind.DAY), None)
