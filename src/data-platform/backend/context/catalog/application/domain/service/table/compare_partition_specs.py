"""Define the compare_partition_specs domain service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.application.domain.model.table import (
    PartitionChange,
    PartitionField,
    PartitionFieldComparison,
    PartitionSpec,
    PartitionSpecComparison,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

_VOID = "void"


def _default_suffix(transform: str) -> str | None:
    """Return the suffix Iceberg appends to the source column name for ``transform``, None if unknown.

    The rule is PyIceberg's ``_PartitionNameGenerator`` (``pyiceberg/partitioning.py``).
    """
    kind, _, argument = transform.partition("[")
    number = argument.removesuffix("]")
    return {
        "identity": "",
        "year": "_year",
        "month": "_month",
        "day": "_day",
        "hour": "_hour",
        "bucket": f"_bucket_{number}",
        "truncate": f"_trunc_{number}",
    }.get(kind)


def _is_default_name(name: str, transform: str, source_path: tuple[str, ...]) -> bool:
    suffix = _default_suffix(transform)
    if suffix is None:
        return False
    return name in {f"{'.'.join(source_path)}{suffix}", f"{'_'.join(source_path)}{suffix}"}


def _source_path(field: PartitionField, column_paths: Mapping[int, tuple[str, ...]]) -> tuple[str, ...]:
    return column_paths.get(field.source_id, (f"#{field.source_id}",))


def _renamed(
    current: PartitionField,
    current_path: tuple[str, ...],
    previous: PartitionField,
    previous_path: tuple[str, ...],
) -> bool:
    """A name change is a rename unless both names are Iceberg's default for their transforms."""
    if current.name == previous.name:
        return False
    return not (
        _is_default_name(current.name, current.transform, current_path)
        and _is_default_name(previous.name, previous.transform, previous_path)
    )


def _added(current: PartitionField, column_paths: Mapping[int, tuple[str, ...]]) -> PartitionFieldComparison:
    return PartitionFieldComparison(
        field_id=current.field_id,
        previous_field_id=None,
        name=current.name,
        previous_name=None,
        source_path=_source_path(current, column_paths),
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
        source_path=None,
        previous_source_path=_source_path(previous, column_paths),
        transform=None,
        previous_transform=previous.transform,
        changes=(PartitionChange.REMOVED,),
    )


def _matched(
    current: PartitionField, previous: PartitionField, column_paths: Mapping[int, tuple[str, ...]]
) -> PartitionFieldComparison:
    current_path = _source_path(current, column_paths)
    previous_path = _source_path(previous, column_paths)
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
        source_path=current_path,
        previous_source_path=previous_path,
        transform=current.transform,
        previous_transform=previous.transform,
        changes=changes,
    )


def _live(spec: PartitionSpec) -> tuple[PartitionField, ...]:
    """Return the fields of ``spec`` that partition something: a ``void`` field is a dropped one."""
    return tuple(field for field in spec.fields if field.transform != _VOID)


def compare_partition_specs(
    base: PartitionSpec | None, spec: PartitionSpec, column_paths: Mapping[int, tuple[str, ...]]
) -> PartitionSpecComparison:
    """Return ``spec`` set against ``base``, matching partition fields by id, then by source column.

    Iceberg gives a field with a new transform a new partition field id, so a removed and an added
    field on the same source column are paired into one row carrying ``TRANSFORM_CHANGED``. A
    ``void`` field (format v1's way of dropping a field) counts as absent: removed against a base
    that had it live, left out when it is ``void`` on both sides. A name change is ``RENAMED``
    unless both names are Iceberg's default for their transforms. A source id missing from
    ``column_paths`` reads as ``#<id>``. With no ``base`` every field is listed unchanged. Rows
    follow ``spec``'s field order, then unpaired removed fields in ``base`` order.
    """
    current_fields = _live(spec)
    if base is None:
        rows = [_matched(field, field, column_paths) for field in current_fields]
        return PartitionSpecComparison(base_spec_id=None, spec_id=spec.spec_id, fields=tuple(rows))
    previous_fields = _live(base)
    previous_by_id = {field.field_id: field for field in previous_fields}
    current_ids = {field.field_id for field in current_fields}
    unpaired = [field for field in previous_fields if field.field_id not in current_ids]
    rows: list[PartitionFieldComparison] = []
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
