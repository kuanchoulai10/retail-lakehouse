"""Define the ListTablePartitionSpecVersionsUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class ListTablePartitionSpecVersionsUseCaseInput(UseCaseInput):
    """Name the table by catalog, namespace parts and name."""

    catalog: str
    namespace: tuple[str, ...]
    name: str
