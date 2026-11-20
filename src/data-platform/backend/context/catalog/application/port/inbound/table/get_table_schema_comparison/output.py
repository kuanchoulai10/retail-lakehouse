"""Define the GetTableSchemaComparisonUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class GetTableSchemaComparisonUseCaseOutput(UseCaseOutput):
    """Carry the base version, the compared version and every field of the compared version matched by field id."""

    class Field(UseCaseOutput):
        """One field in both versions; the current side is None when removed, the previous side None when added.

        ``changes`` holds ``added``, ``removed``, ``renamed``, ``type_changed``,
        ``nullability_changed`` and ``doc_changed``; empty means unchanged.
        """

        field_id: int
        depth: int
        path: tuple[str, ...] | None
        previous_path: tuple[str, ...] | None
        type: str | None
        previous_type: str | None
        required: bool | None
        previous_required: bool | None
        doc: str | None
        previous_doc: str | None
        changes: tuple[str, ...]

    base_schema_id: int | None
    schema_id: int
    items: tuple[Field, ...]
