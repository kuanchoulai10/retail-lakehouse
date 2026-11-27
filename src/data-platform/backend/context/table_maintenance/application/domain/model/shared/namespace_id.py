"""Define the NamespaceId identifier."""

from __future__ import annotations

from pydantic import field_validator

from base import EntityId

_SEPARATOR = "\x1f"


class NamespaceId(EntityId):
    """Identify a namespace by its catalog and its levels, joined by the unit separator U+001F.

    A level is one part of the namespace and may hold dots: ``eu.west`` given as one level stays one.
    A table name spells its namespace dot-joined, so ``enclosing`` splits it on the dots.
    """

    @field_validator("root")
    @classmethod
    def _names_a_catalog_and_a_level(cls, value: str) -> str:
        """Refuse a value that is not a non-empty catalog and at least one non-empty level."""
        parts = value.split(_SEPARATOR)
        if len(parts) < 2 or any(not part for part in parts):  # noqa: PLR2004
            raise ValueError("a namespace id names a catalog and at least one level, none of them empty")
        return value

    @classmethod
    def of(cls, catalog: str, levels: tuple[str, ...]) -> NamespaceId:
        """Return the id of the namespace made of ``levels`` in ``catalog``; ValueError on a U+001F inside one."""
        if any(_SEPARATOR in part for part in (catalog, *levels)):
            raise ValueError("a catalog name or namespace level holds no U+001F")
        return cls(_SEPARATOR.join((catalog, *levels)))

    @classmethod
    def enclosing(cls, catalog: str, namespace: str) -> tuple[NamespaceId, ...]:
        """Return the namespaces enclosing a table of ``catalog`` in the dot-joined ``namespace``, deepest first.

        An empty namespace is enclosed by none.
        """
        levels = tuple(namespace.split(".")) if namespace else ()
        return tuple(cls.of(catalog, levels[:depth]) for depth in range(len(levels), 0, -1))

    @property
    def catalog(self) -> str:
        """Return the name of the catalog holding the namespace."""
        return self.value.split(_SEPARATOR)[0]

    @property
    def levels(self) -> tuple[str, ...]:
        """Return the levels of the namespace, outermost first."""
        return tuple(self.value.split(_SEPARATOR)[1:])
