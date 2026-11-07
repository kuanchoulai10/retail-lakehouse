"""Define the CreateGenericTableUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CreateGenericTableUseCaseInput:
    """Carry the create generic table form: name, format, optional base location and doc, properties.

    A blank base location or doc counts as absent.
    """

    catalog: str
    namespace: list[str]
    name: str
    format: str
    base_location: str | None = None
    doc: str | None = None
    properties: dict[str, str] = field(default_factory=dict)
