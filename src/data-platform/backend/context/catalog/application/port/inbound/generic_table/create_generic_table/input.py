"""Define the CreateGenericTableUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class CreateGenericTableUseCaseInput(UseCaseInput):
    """Carry the create generic table form: name, format, optional base location and doc, properties.

    A blank base location or doc counts as absent.
    """

    catalog: str
    namespace: tuple[str, ...]
    name: str
    format: str
    base_location: str | None = None
    doc: str | None = None
    properties: dict[str, str] = {}
