"""Define the NamespaceId identifier."""

from __future__ import annotations

from dataclasses import dataclass

from base import EntityId

_SEPARATOR = "\x1f"


@dataclass(frozen=True)
class NamespaceId(EntityId):
    """Identify a namespace by its catalog and its parts, joined by the unit separator U+001F.

    A part is one level of the namespace and may hold dots or spaces: ``a.b`` is one part.
    """

    @classmethod
    def of(cls, catalog: str, parts: tuple[str, ...]) -> NamespaceId:
        """Return the id of the namespace made of ``parts`` in ``catalog``."""
        return cls(_SEPARATOR.join((catalog, *parts)))

    @property
    def catalog(self) -> str:
        """Return the name of the catalog holding the namespace."""
        return self.value.split(_SEPARATOR)[0]

    @property
    def parts(self) -> tuple[str, ...]:
        """Return the parts of the namespace, outermost first."""
        return tuple(self.value.split(_SEPARATOR)[1:])
