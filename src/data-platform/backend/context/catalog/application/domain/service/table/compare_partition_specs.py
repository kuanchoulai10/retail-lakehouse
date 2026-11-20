"""Define the compare_partition_specs domain service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.application.domain.model.table import (
    DefaultPartitionFieldNames,
    PartitionChange,
    PartitionField,
    PartitionFieldComparison,
    PartitionSpec,
    PartitionSpecComparison,
    PartitionTransformKind,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

_DEFAULT_NAMES = DefaultPartitionFieldNames()


def _renamed(
    current: PartitionField,
    current_path: tuple[str, ...] | None,
    previous: PartitionField,
    previous_path: tuple[str, ...] | None,
) -> bool:
    """A name change is a rename unless both names are Iceberg's default for their transforms."""
    if current.name == previous.name:
        return False
    return not (
        _DEFAULT_NAMES.is_default(current.name, current.transform, current_path)
        and _DEFAULT_NAMES.is_default(previous.name, previous.transform, previous_path)
    )


def _added(current: PartitionField, column_paths: Mapping[int, tuple[str, ...]]) -> PartitionFieldComparison:
    return PartitionFieldComparison(
        field_id=current.field_id,
        previous_field_id=None,
        name=current.name,
        previous_name=None,
        source_id=current.source_id,
        previous_source_id=None,
        source_path=column_paths.get(current.source_id),
        previous_source_path=None,
        transform=current.transform,
        previous_transform=None,
        changes=(PartitionChange.ADDED,),
    )


def _removed(previous: PartitionField, column_paths: Mapping[int, tuple[str, ...]]) -> PartitionFieldComparison:
    return PartitionFieldComparison(
        field_id=None,
        previous_field_id=previous.field_id,
        name=None,
        previous_name=previous.name,
        source_id=None,
        previous_source_id=previous.source_id,
        source_path=None,
        previous_source_path=column_paths.get(previous.source_id),
        transform=None,
        previous_transform=previous.transform,
        changes=(PartitionChange.REMOVED,),
    )


def _matched(
    current: PartitionField, previous: PartitionField, column_paths: Mapping[int, tuple[str, ...]]
) -> PartitionFieldComparison:
    current_path = column_paths.get(current.source_id)
    previous_path = column_paths.get(previous.source_id)
    changes = tuple(
        kind
        for kind, changed in (
            (PartitionChange.RENAMED, _renamed(current, current_path, previous, previous_path)),
            (PartitionChange.TRANSFORM_CHANGED, current.transform != previous.transform),
        )
        if changed
    )
    return PartitionFieldComparison(
        field_id=current.field_id,
        previous_field_id=previous.field_id,
        name=current.name,
        previous_name=previous.name,
        source_id=current.source_id,
        previous_source_id=previous.source_id,
        source_path=current_path,
        previous_source_path=previous_path,
        transform=current.transform,
        previous_transform=previous.transform,
        changes=changes,
    )


def _live(spec: PartitionSpec) -> tuple[PartitionField, ...]:
    """Return the fields of ``spec`` that partition something: a ``void`` field is a dropped one."""
    return tuple(field for field in spec.fields if field.transform.kind is not PartitionTransformKind.VOID)


def compare_partition_specs(
    base: PartitionSpec | None, spec: PartitionSpec, column_paths: Mapping[int, tuple[str, ...]]
) -> PartitionSpecComparison:
    """Return ``spec`` set against ``base``, matching partition fields by id, then by source column.

    Iceberg gives a field with a new transform a new partition field id, so a removed and an added
    field on the same source column are paired into one row carrying ``TRANSFORM_CHANGED``. A
    ``void`` field (format v1's way of dropping a field) counts as absent: removed against a base
    that had it live, left out when it is ``void`` on both sides. A name change is ``RENAMED``
    unless both names are default names (``DefaultPartitionFieldNames``). A source id missing
    from ``column_paths`` has no source path. With no ``base`` every field is listed unchanged.
    Rows follow ``spec``'s field order, then unpaired removed fields in ``base`` order.
    """
    current_fields = _live(spec)
    rows: list[PartitionFieldComparison]
    if base is None:
        rows = [_matched(field, field, column_paths) for field in current_fields]
        return PartitionSpecComparison(base_spec_id=None, spec_id=spec.spec_id, fields=tuple(rows))
    previous_fields = _live(base)
    previous_by_id = {field.field_id: field for field in previous_fields}
    current_ids = {field.field_id for field in current_fields}
    unpaired = [field for field in previous_fields if field.field_id not in current_ids]
    rows = []
    for field in current_fields:
        if field.field_id in previous_by_id:
            rows.append(_matched(field, previous_by_id[field.field_id], column_paths))
            continue
        same_source = next((old for old in unpaired if old.source_id == field.source_id), None)
        if same_source is None:
            rows.append(_added(field, column_paths))
        else:
            unpaired.remove(same_source)
            rows.append(_matched(field, same_source, column_paths))
    rows.extend(_removed(field, column_paths) for field in unpaired)
    return PartitionSpecComparison(base_spec_id=base.spec_id, spec_id=spec.spec_id, fields=tuple(rows))
