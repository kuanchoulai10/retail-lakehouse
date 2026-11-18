"""Define the CreateGenericTableUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class CreateGenericTableUseCaseOutput(UseCaseOutput):
    """Describe the generic table as the catalog saved it, every field primitive."""

    catalog: str
    namespace: tuple[str, ...]
    name: str
    format: str
    base_location: str | None
    doc: str | None
    properties: dict[str, str]
