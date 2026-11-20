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


def _removed_after_neighbour(
    rows: list[SchemaFieldComparison], base_walk: tuple[SchemaFieldAtPath, ...], gone: list[SchemaFieldAtPath]
) -> list[SchemaFieldComparison]:
    """Place each removed row right after the nearest field before it in the base that is in the list."""
    base_ids = [walked.field.id for walked in base_walk]
    for removed in gone:
        position = base_ids.index(removed.field.id)
        listed = {row.field_id: index for index, row in enumerate(rows)}
        anchor = next((listed[base_ids[i]] for i in range(position - 1, -1, -1) if base_ids[i] in listed), -1)
        rows.insert(anchor + 1, _removed(removed))
    return rows


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
    gone = [walked for walked in base_walk if walked.field.id not in current_ids]
    rows = _removed_after_neighbour(rows, base_walk, gone)
    return SchemaComparison(base_schema_id=base.schema_id, schema_id=schema.schema_id, fields=tuple(rows))
