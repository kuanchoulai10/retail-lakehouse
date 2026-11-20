"""Define the GetTablePartitionSpecComparisonUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class GetTablePartitionSpecComparisonUseCaseOutput(UseCaseOutput):
    """Carry the base version, the compared version and every partition field of the compared version."""

    class Field(UseCaseOutput):
        """One partition field in both versions; the current side is None when removed, the previous when added.

        ``transform`` and ``previous_transform`` are Iceberg's text form (``day``,
        ``bucket[16]``). A side that is there carries its source column id; its source path is
        None when no schema of the table holds that column. ``changes`` holds ``added``,
        ``removed``, ``renamed`` and ``transform_changed``; empty means unchanged.
        """

        field_id: int | None
        previous_field_id: int | None
        name: str | None
        previous_name: str | None
        source_id: int | None
        previous_source_id: int | None
        source_path: tuple[str, ...] | None
        previous_source_path: tuple[str, ...] | None
        transform: str | None
        previous_transform: str | None
        changes: tuple[str, ...]

    base_spec_id: int | None
    spec_id: int
    items: tuple[Field, ...]
