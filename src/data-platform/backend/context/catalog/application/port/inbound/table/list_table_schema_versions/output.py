"""Define the ListTableSchemaVersionsUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class ListTableSchemaVersionsUseCaseOutput(UseCaseOutput):
    """Carry the current schema id and every schema version, newest id first."""

    class Version(UseCaseOutput):
        """One schema version and what it changed against the version below it.

        ``changes`` counts the fields carrying each kind of change (``added``, ``removed``,
        ``renamed``, ``type_changed``, ``nullability_changed``, ``doc_changed``, zeros
        included) and is None for the first version. ``column_count`` is the top-level fields.
        """

        schema_id: int
        previous_schema_id: int | None
        current: bool
        column_count: int
        changes: dict[str, int] | None

    current_schema_id: int
    items: tuple[Version, ...]
