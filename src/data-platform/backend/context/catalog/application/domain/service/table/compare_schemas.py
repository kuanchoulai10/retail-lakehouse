"""Define the compare_schemas domain service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.application.domain.model.table import (
    SchemaChange,
    SchemaComparison,
    SchemaFieldComparison,
)

if TYPE_CHECKING:
    from context.catalog.application.domain.model.shared import Schema, SchemaFieldAtPath


def _added(current: SchemaFieldAtPath) -> SchemaFieldComparison:
    field = current.field
    return SchemaFieldComparison(
        field_id=field.id,
        depth=current.depth,
        path=current.path,
        previous_path=None,
        type=field.outer_type,
        previous_type=None,
        required=field.required,
        previous_required=None,
        doc=field.doc,
        previous_doc=None,
        changes=(SchemaChange.ADDED,),
    )


def _removed(previous: SchemaFieldAtPath) -> SchemaFieldComparison:
    field = previous.field
    return SchemaFieldComparison(
        field_id=field.id,
        depth=previous.depth,
        path=None,
        previous_path=previous.path,
        type=None,
        previous_type=field.outer_type,
        required=None,
        previous_required=field.required,
        doc=None,
        previous_doc=field.doc,
        changes=(SchemaChange.REMOVED,),
    )


def _matched(current: SchemaFieldAtPath, previous: SchemaFieldAtPath) -> SchemaFieldComparison:
    changes = tuple(
        kind
        for kind, changed in (
            (SchemaChange.RENAMED, current.field.name != previous.field.name),
            (SchemaChange.TYPE_CHANGED, current.field.outer_type != previous.field.outer_type),
            (SchemaChange.NULLABILITY_CHANGED, current.field.required != previous.field.required),
            (SchemaChange.DOC_CHANGED, current.field.doc != previous.field.doc),
        )
        if changed
    )
    return SchemaFieldComparison(
        field_id=current.field.id,
        depth=current.depth,
        path=current.path,
        previous_path=previous.path,
        type=current.field.outer_type,
        previous_type=previous.field.outer_type,
        required=current.field.required,
        previous_required=previous.field.required,
        doc=current.field.doc,
        previous_doc=previous.field.doc,
        changes=changes,
    )


def _with_removed_rows(
    rows: list[SchemaFieldComparison], base_walk: tuple[SchemaFieldAtPath, ...], current_ids: set[int]
) -> tuple[SchemaFieldComparison, ...]:
    """Place each removed row right after the field before it in the base, a kept one or another removed one.

    One pass over the base collects, for each kept field, the removed fields that follow it before
    the next kept one; those with no kept field before them come first.
    """
    following: dict[int | None, list[SchemaFieldComparison]] = {}
    kept_before: int | None = None
    for walked in base_walk:
        if walked.field.id in current_ids:
            kept_before = walked.field.id
        else:
            following.setdefault(kept_before, []).append(_removed(walked))
    return (
        *following.get(None, ()),
        *(placed for row in rows for placed in (row, *following.get(row.field_id, ()))),
    )


def compare_schemas(base: Schema | None, schema: Schema) -> SchemaComparison:
    """Return ``schema`` set against ``base``, matching fields by Iceberg field id, never by name.

    A renamed or promoted field is one row carrying every change it made, and a renamed parent
    does not make its children renamed. With no ``base`` (the first version) every field is
    listed unchanged. Rows follow ``schema``'s depth-first order, each removed field placed right
    after the nearest field before it in ``base`` that is in the list (first if none), removed
    fields kept in ``base`` order.
    """
    walk = schema.walk()
    if base is None:
        rows = [_matched(current, current) for current in walk]
        return SchemaComparison(base_schema_id=None, schema_id=schema.schema_id, fields=tuple(rows))
    base_walk = base.walk()
    previous_by_id = {walked.field.id: walked for walked in base_walk}
    current_ids = {walked.field.id for walked in walk}
    rows = [
        _matched(current, previous_by_id[current.field.id]) if current.field.id in previous_by_id else _added(current)
        for current in walk
    ]
    fields = _with_removed_rows(rows, base_walk, current_ids)
    return SchemaComparison(base_schema_id=base.schema_id, schema_id=schema.schema_id, fields=fields)
