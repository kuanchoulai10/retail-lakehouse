"""Test comparing two partition specs by partition field id, pairing transform changes by source column."""

from __future__ import annotations

import pytest

from base import InvariantViolation
from context.catalog.application.domain.model.table import (
    PartitionChange,
    PartitionField,
    PartitionFieldComparison,
    PartitionSpec,
    PartitionTransform,
    PartitionTransformKind,
)
from context.catalog.application.domain.service.table import compare_partition_specs

PATHS = {2: ("customer_id",), 3: ("order_ts",)}
IDENTITY = PartitionTransform(kind=PartitionTransformKind.IDENTITY)
MONTH = PartitionTransform(kind=PartitionTransformKind.MONTH)
DAY = PartitionTransform(kind=PartitionTransformKind.DAY)
HOUR = PartitionTransform(kind=PartitionTransformKind.HOUR)
VOID = PartitionTransform(kind=PartitionTransformKind.VOID)


def _bucket(count: int) -> PartitionTransform:
    return PartitionTransform(kind=PartitionTransformKind.BUCKET, argument=count)


def _truncate(width: int) -> PartitionTransform:
    return PartitionTransform(kind=PartitionTransformKind.TRUNCATE, argument=width)


def _pfield(field_id: int, name: str, transform: PartitionTransform, source_id: int) -> PartitionField:
    return PartitionField(source_id=source_id, field_id=field_id, name=name, transform=transform)


def _spec(spec_id: int, *fields: PartitionField) -> PartitionSpec:
    return PartitionSpec(spec_id=spec_id, fields=fields)


def test_added_bucket_field():
    """A new partition field is one added row carrying its transform and source column."""
    base = _spec(0, _pfield(1000, "order_ts_day", DAY, 3))
    new = _spec(1, _pfield(1000, "order_ts_day", DAY, 3), _pfield(1001, "customer_id_bucket_16", _bucket(16), 2))
    comparison = compare_partition_specs(base, new, PATHS)
    kept, added = comparison.fields
    assert (comparison.base_spec_id, comparison.spec_id) == (0, 1)
    assert kept.changes == ()
    assert (kept.field_id, kept.previous_field_id) == (1000, 1000)
    assert added.changes == (PartitionChange.ADDED,)
    assert (added.field_id, added.previous_field_id) == (1001, None)
    assert (added.name, added.previous_name) == ("customer_id_bucket_16", None)
    assert (added.source_path, added.previous_source_path) == (("customer_id",), None)
    assert (added.source_id, added.previous_source_id) == (2, None)
    assert (added.transform, added.previous_transform) == (_bucket(16), None)


def test_day_to_hour_with_default_names_is_only_a_transform_change():
    """A new transform gets a new id and pairs with the old field by source column; default names are no rename."""
    base = _spec(0, _pfield(1000, "order_ts_day", DAY, 3))
    new = _spec(1, _pfield(1001, "order_ts_hour", HOUR, 3))
    (row,) = compare_partition_specs(base, new, PATHS).fields
    assert (row.field_id, row.previous_field_id) == (1001, 1000)
    assert row.changes == (PartitionChange.TRANSFORM_CHANGED,)
    assert (row.name, row.previous_name) == ("order_ts_hour", "order_ts_day")
    assert (row.previous_transform, row.transform) == (DAY, HOUR)
    assert (row.previous_source_path, row.source_path) == (("order_ts",), ("order_ts",))


def test_bucket_and_truncate_default_names_carry_their_number():
    """Iceberg names these fields ``_bucket_<N>`` and ``_trunc_<W>``, so changing N is only a transform change."""
    base = _spec(0, _pfield(1000, "customer_id_bucket_16", _bucket(16), 2))
    new = _spec(1, _pfield(1001, "customer_id_bucket_32", _bucket(32), 2))
    (row,) = compare_partition_specs(base, new, PATHS).fields
    assert row.changes == (PartitionChange.TRANSFORM_CHANGED,)
    truncated = _spec(2, _pfield(1002, "customer_id_trunc_4", _truncate(4), 2))
    (row,) = compare_partition_specs(new, truncated, PATHS).fields
    assert row.changes == (PartitionChange.TRANSFORM_CHANGED,)


def test_identity_default_name_is_the_source_column():
    """An identity field is named after its source column, so identity to day is only a transform change."""
    base = _spec(0, _pfield(1000, "order_ts", IDENTITY, 3))
    new = _spec(1, _pfield(1001, "order_ts_day", DAY, 3))
    (row,) = compare_partition_specs(base, new, PATHS).fields
    assert row.changes == (PartitionChange.TRANSFORM_CHANGED,)


def test_renamed_field_keeps_its_id():
    """A field with the same id and transform under a new name is a rename."""
    base = _spec(0, _pfield(1000, "ts_day", DAY, 3))
    new = _spec(1, _pfield(1000, "order_day", DAY, 3))
    (row,) = compare_partition_specs(base, new, PATHS).fields
    assert row.changes == (PartitionChange.RENAMED,)
    assert (row.field_id, row.previous_field_id) == (1000, 1000)
    assert (row.previous_name, row.name) == ("ts_day", "order_day")
    assert (row.previous_transform, row.transform) == (DAY, DAY)


def test_custom_name_on_a_new_transform_is_renamed_and_transform_changed():
    """A transform change whose new name is not Iceberg's default carries both tags."""
    base = _spec(0, _pfield(1000, "order_ts_day", DAY, 3))
    new = _spec(1, _pfield(1001, "placed_hour", HOUR, 3))
    (row,) = compare_partition_specs(base, new, PATHS).fields
    assert row.changes == (PartitionChange.RENAMED, PartitionChange.TRANSFORM_CHANGED)


def test_custom_old_name_on_a_new_transform_is_renamed_and_transform_changed():
    """A custom name on the old side and a default one on the new side is still a rename."""
    base = _spec(0, _pfield(1000, "placed_day", DAY, 3))
    new = _spec(1, _pfield(1001, "order_ts_hour", HOUR, 3))
    (row,) = compare_partition_specs(base, new, PATHS).fields
    assert row.changes == (PartitionChange.RENAMED, PartitionChange.TRANSFORM_CHANGED)


def test_removed_field_comes_after_the_newer_spec_fields():
    """A removed field is one row with the current side empty, listed after the newer spec's fields."""
    base = _spec(0, _pfield(1000, "order_ts_day", DAY, 3), _pfield(1001, "customer_id_bucket_16", _bucket(16), 2))
    new = _spec(1, _pfield(1001, "customer_id_bucket_16", _bucket(16), 2))
    kept, removed = compare_partition_specs(base, new, PATHS).fields
    assert kept.changes == ()
    assert removed.changes == (PartitionChange.REMOVED,)
    assert (removed.field_id, removed.previous_field_id) == (None, 1000)
    assert (removed.name, removed.previous_name) == (None, "order_ts_day")
    assert (removed.source_id, removed.previous_source_id) == (None, 3)
    assert (removed.source_path, removed.previous_source_path) == (None, ("order_ts",))
    assert (removed.transform, removed.previous_transform) == (None, DAY)


def test_v1_void_counts_as_removed():
    """A v1 field dropped by turning it into void is a removal, not a change to ``void``."""
    base = _spec(0, _pfield(1000, "order_ts_day", DAY, 3))
    new = _spec(1, _pfield(1000, "order_ts_day", VOID, 3))
    comparison = compare_partition_specs(base, new, PATHS)
    (row,) = comparison.fields
    assert row.changes == (PartitionChange.REMOVED,)
    assert (row.transform, row.previous_transform) == (None, DAY)
    assert comparison.field_count() == 0


def test_void_in_both_versions_is_left_out():
    """A field that is void in both versions is not listed."""
    base = _spec(0, _pfield(1000, "order_ts_day", VOID, 3), _pfield(1001, "customer_id_bucket_16", _bucket(16), 2))
    new = _spec(1, _pfield(1000, "order_ts_day", VOID, 3), _pfield(1001, "customer_id_bucket_16", _bucket(16), 2))
    comparison = compare_partition_specs(base, new, PATHS)
    assert [row.field_id for row in comparison.fields] == [1001]
    assert comparison.field_count() == 1


def test_a_void_field_in_the_newer_spec_only_is_left_out():
    """A void field with no counterpart in the base is neither added nor counted."""
    comparison = compare_partition_specs(_spec(0), _spec(1, _pfield(1000, "order_ts_day", VOID, 3)), PATHS)
    assert comparison.fields == ()
    assert comparison.field_count() == 0


@pytest.mark.parametrize("side", ["transform", "previous_transform"])
def test_a_comparison_row_never_holds_a_void_transform(side: str):
    """A void field is a dropped one, so a row that holds a void transform on either side is refused."""
    row = PartitionFieldComparison(
        field_id=1000,
        previous_field_id=1000,
        name="order_ts_day",
        previous_name="order_ts_day",
        source_id=3,
        previous_source_id=3,
        source_path=("order_ts",),
        previous_source_path=("order_ts",),
        transform=DAY,
        previous_transform=DAY,
        changes=(),
    )
    with pytest.raises(InvariantViolation, match="void"):
        row.with_changes(**{side: VOID})


def test_unknown_source_column_has_no_path_but_keeps_its_id():
    """A source id missing from the column paths has no path; the row keeps the id."""
    (row,) = compare_partition_specs(None, _spec(0, _pfield(1000, "region", IDENTITY, 7)), PATHS).fields
    assert (row.source_id, row.source_path) == (7, None)
    assert (row.previous_source_id, row.previous_source_path) == (7, None)


def test_an_unknown_transform_is_compared_by_its_text():
    """Two unknown transforms with one text are the same; another text is a transform change."""
    zorder = PartitionTransform(kind=PartitionTransformKind.UNKNOWN, raw="zorder")
    other = PartitionTransform(kind=PartitionTransformKind.UNKNOWN, raw="hilbert")
    base = _spec(0, _pfield(1000, "order_ts_z", zorder, 3))
    (same,) = compare_partition_specs(base, _spec(1, _pfield(1000, "order_ts_z", zorder, 3)), PATHS).fields
    (changed,) = compare_partition_specs(base, _spec(1, _pfield(1000, "order_ts_z", other, 3)), PATHS).fields
    assert same.changes == ()
    assert changed.changes == (PartitionChange.TRANSFORM_CHANGED,)


def test_no_base_lists_every_field_unchanged():
    """With no earlier spec every field is listed unchanged and nothing is added."""
    comparison = compare_partition_specs(
        None,
        _spec(0, _pfield(1000, "order_ts_day", DAY, 3), _pfield(1001, "customer_id_bucket_16", _bucket(16), 2)),
        PATHS,
    )
    assert comparison.base_spec_id is None
    assert [row.changes for row in comparison.fields] == [(), ()]
    assert [(row.field_id, row.previous_field_id) for row in comparison.fields] == [(1000, 1000), (1001, 1001)]
    assert comparison.fields[0].transform == comparison.fields[0].previous_transform == DAY
    assert comparison.field_count() == 2


def test_unpartitioned_to_partitioned():
    """Partitioning a table that had no spec fields adds one row, and the newer spec has one field."""
    comparison = compare_partition_specs(_spec(0), _spec(1, _pfield(1000, "order_ts_day", DAY, 3)), PATHS)
    (row,) = comparison.fields
    assert row.changes == (PartitionChange.ADDED,)
    assert comparison.field_count() == 1


def test_partitioned_to_unpartitioned_counts_no_field():
    """Dropping every field leaves removed rows and a newer spec with no field."""
    comparison = compare_partition_specs(_spec(0, _pfield(1000, "order_ts_day", DAY, 3)), _spec(1), PATHS)
    assert [row.changes for row in comparison.fields] == [(PartitionChange.REMOVED,)]
    assert comparison.field_count() == 0


def test_change_counts_cover_every_kind():
    """Counts hold every kind, zeros included, and count a row once per tag it carries."""
    base = _spec(0, _pfield(1000, "order_ts_day", DAY, 3), _pfield(1001, "customer_id_bucket_16", _bucket(16), 2))
    new = _spec(1, _pfield(1002, "placed_hour", HOUR, 3), _pfield(1003, "region", IDENTITY, 7))
    counts = compare_partition_specs(base, new, PATHS).change_counts()
    assert counts == {
        PartitionChange.ADDED: 1,
        PartitionChange.REMOVED: 1,
        PartitionChange.RENAMED: 1,
        PartitionChange.TRANSFORM_CHANGED: 1,
    }


def test_two_fields_on_one_source_pair_in_order():
    """Each removed field pairs with at most one added field of the same source column."""
    base = _spec(0, _pfield(1000, "order_ts_day", DAY, 3), _pfield(1001, "order_ts_hour", HOUR, 3))
    new = _spec(1, _pfield(1002, "order_ts_month", MONTH, 3))
    first, second = compare_partition_specs(base, new, PATHS).fields
    assert (first.field_id, first.previous_field_id, first.changes) == (
        1002,
        1000,
        (PartitionChange.TRANSFORM_CHANGED,),
    )
    assert (second.field_id, second.previous_field_id, second.changes) == (None, 1001, (PartitionChange.REMOVED,))


def test_change_counts_include_zero_counts():
    """A kind no field carries is still listed, with 0."""
    comparison = compare_partition_specs(
        _spec(0, _pfield(1000, "order_ts_day", DAY, 3)),
        _spec(1, _pfield(1000, "order_ts_day", DAY, 3), _pfield(1001, "customer_id_bucket_16", _bucket(16), 2)),
        PATHS,
    )
    assert comparison.change_counts() == {
        PartitionChange.ADDED: 1,
        PartitionChange.REMOVED: 0,
        PartitionChange.RENAMED: 0,
        PartitionChange.TRANSFORM_CHANGED: 0,
    }


def test_java_unnumbered_bucket_name_is_a_default():
    """Java names a bucket field ``<src>_bucket`` (CREATE) or ``<src>_bucket_<N>`` (ALTER): both are defaults."""
    base = _spec(0, _pfield(1000, "customer_id_bucket", _bucket(16), 2))
    new = _spec(1, _pfield(1001, "customer_id_bucket_32", _bucket(32), 2))
    (row,) = compare_partition_specs(base, new, PATHS).fields
    assert row.changes == (PartitionChange.TRANSFORM_CHANGED,)


def test_java_unnumbered_truncate_name_is_a_default():
    """Java names a truncate field ``<src>_trunc`` (CREATE) or ``<src>_trunc_<W>`` (ALTER): both are defaults."""
    base = _spec(0, _pfield(1000, "customer_id_trunc", _truncate(4), 2))
    new = _spec(1, _pfield(1001, "customer_id_trunc_8", _truncate(8), 2))
    (row,) = compare_partition_specs(base, new, PATHS).fields
    assert row.changes == (PartitionChange.TRANSFORM_CHANGED,)


def test_default_name_of_a_nested_source_column_is_dotted():
    """Java builds the default name from the dotted column name, so ``address.zip_day`` is a default."""
    paths = {5: ("address", "zip")}
    base = _spec(0, _pfield(1000, "address.zip_day", DAY, 5))
    new = _spec(1, _pfield(1001, "address.zip_hour", HOUR, 5))
    (row,) = compare_partition_specs(base, new, paths).fields
    assert row.changes == (PartitionChange.TRANSFORM_CHANGED,)
    assert row.source_path == ("address", "zip")
    underscored = _spec(2, _pfield(1002, "address_zip_hour", HOUR, 5))
    (row,) = compare_partition_specs(base, underscored, paths).fields
    assert row.changes == (PartitionChange.RENAMED, PartitionChange.TRANSFORM_CHANGED)
