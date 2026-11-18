"""Define the GetGenericTableUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class GetGenericTableUseCaseOutput(UseCaseOutput):
    """Describe the generic table, every field primitive."""

    catalog: str
    namespace: tuple[str, ...]
    name: str
    format: str
    base_location: str | None
    doc: str | None
    properties: dict[str, str]
