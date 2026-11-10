"""Define the GenericTableId identifier."""

from __future__ import annotations

from base import EntityId
from context.catalog.application.domain.model.shared import reject_unit_separator

_SEPARATOR = "\x1f"


class GenericTableId(EntityId):
    """Identify a generic table by its catalog, its namespace parts and its name, joined by U+001F.

    A namespace part may hold dots or spaces: ``a.b`` is one part.
    """

    @classmethod
    def of(cls, catalog: str, namespace: tuple[str, ...], name: str) -> GenericTableId:
        """Return the id of the generic table ``name`` in the namespace ``namespace`` of ``catalog``."""
        reject_unit_separator("catalog name", catalog)
        reject_unit_separator("namespace parts", *namespace)
        reject_unit_separator("generic table name", name)
        return cls(_SEPARATOR.join((catalog, *namespace, name)))

    @property
    def catalog(self) -> str:
        """Return the name of the catalog holding the generic table."""
        return self.value.split(_SEPARATOR)[0]

    @property
    def namespace(self) -> tuple[str, ...]:
        """Return the parts of the namespace holding the generic table, outermost first."""
        return tuple(self.value.split(_SEPARATOR)[1:-1])

    @property
    def name(self) -> str:
        """Return the generic table's name inside its namespace."""
        return self.value.split(_SEPARATOR)[-1]
