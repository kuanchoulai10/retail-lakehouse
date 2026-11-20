"""Define the GetTablePartitionSpecComparisonUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class GetTablePartitionSpecComparisonUseCaseInput(UseCaseInput):
    """Name the table and the spec version; the base is another version, or the previous one when None."""

    catalog: str
    namespace: tuple[str, ...]
    name: str
    spec_id: int
    base_spec_id: int | None = None
