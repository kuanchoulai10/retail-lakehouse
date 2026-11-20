"""Define the GetTablePartitionSpecComparisonUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class GetTablePartitionSpecComparisonUseCaseOutput(UseCaseOutput):
    """Carry the base version, the compared version and every partition field of the compared version."""

    class Field(UseCaseOutput):
        """One partition field in both versions; the current side is None when removed, the previous when added.

        ``expression`` and ``previous_expression`` are ``transform(source column)`` text, None
        when that side is absent. ``changes`` holds ``added``, ``removed``, ``renamed`` and
        ``transform_changed``; empty means unchanged.
        """

        field_id: int | None
        previous_field_id: int | None
        name: str | None
        previous_name: str | None
        source_path: tuple[str, ...] | None
        previous_source_path: tuple[str, ...] | None
        transform: str | None
        previous_transform: str | None
        changes: tuple[str, ...]
        expression: str | None
        previous_expression: str | None

    base_spec_id: int | None
    spec_id: int
    items: tuple[Field, ...]
