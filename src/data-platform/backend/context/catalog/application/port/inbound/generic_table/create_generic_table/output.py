"""Define the CreateGenericTableUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CreateGenericTableUseCaseOutput:
    """Describe the generic table as the catalog saved it, every field primitive."""

    catalog: str
    namespace: list[str]
    name: str
    format: str
    base_location: str | None
    doc: str | None
    properties: dict[str, str]
