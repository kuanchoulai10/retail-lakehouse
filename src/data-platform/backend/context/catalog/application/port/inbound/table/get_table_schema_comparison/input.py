"""Define the GetTableSchemaComparisonUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class GetTableSchemaComparisonUseCaseInput(UseCaseInput):
    """Name the table and the schema version; the base is another version, or the previous one when None."""

    catalog: str
    namespace: tuple[str, ...]
    name: str
    schema_id: int
    base_schema_id: int | None = None
