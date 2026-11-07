"""Define the GetGenericTableUseCaseOutput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GetGenericTableUseCaseOutput:
    """Describe the generic table, every field primitive."""

    catalog: str
    namespace: list[str]
    name: str
    format: str
    base_location: str | None
    doc: str | None
    properties: dict[str, str]
