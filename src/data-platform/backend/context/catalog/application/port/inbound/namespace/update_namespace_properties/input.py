"""Define the UpdateNamespacePropertiesUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class UpdateNamespacePropertiesUseCaseInput:
    """Carry the properties to set (``updates``) and the property keys to remove (``removals``)."""

    catalog: str
    namespace: list[str]
    updates: dict[str, str] = field(default_factory=dict)
    removals: list[str] = field(default_factory=list)
