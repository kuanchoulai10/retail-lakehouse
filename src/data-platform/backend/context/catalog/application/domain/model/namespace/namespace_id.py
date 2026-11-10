"""Define the NamespaceId identifier."""

from __future__ import annotations

from base import EntityId
from context.catalog.application.domain.model.shared import reject_unit_separator

_SEPARATOR = "\x1f"


class NamespaceId(EntityId):
    """Identify a namespace by its catalog and its parts, joined by the unit separator U+001F.

    A part is one level of the namespace and may hold dots or spaces: ``a.b`` is one part.
    """

    @classmethod
    def of(cls, catalog: str, parts: tuple[str, ...]) -> NamespaceId:
        """Return the id of the namespace made of ``parts`` in ``catalog``; ValueError on a U+001F inside one."""
        reject_unit_separator("catalog name", catalog)
        reject_unit_separator("namespace parts", *parts)
        return cls(_SEPARATOR.join((catalog, *parts)))

    @property
    def catalog(self) -> str:
        """Return the name of the catalog holding the namespace."""
        return self.value.split(_SEPARATOR)[0]

    @property
    def parts(self) -> tuple[str, ...]:
        """Return the parts of the namespace, outermost first."""
        return tuple(self.value.split(_SEPARATOR)[1:])
