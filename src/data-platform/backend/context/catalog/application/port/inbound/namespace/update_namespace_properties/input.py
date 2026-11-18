"""Define the UpdateNamespacePropertiesUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class UpdateNamespacePropertiesUseCaseInput(UseCaseInput):
    """Carry the properties to set (``updates``) and the property keys to remove (``removals``)."""

    catalog: str
    namespace: tuple[str, ...]
    updates: dict[str, str] = {}
    removals: tuple[str, ...] = ()
